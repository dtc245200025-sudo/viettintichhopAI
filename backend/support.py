import json
import re
from typing import Any

import mysql.connector.errors
from fastapi import BackgroundTasks, FastAPI, Request

from backend.ai import AIProvider
from backend.auth import _require_role, current_user
from backend.chats import _id, _mutate
from backend.db import Database, Transaction
from backend.errors import ApiError
from backend.automation import conversation_summary, select_agent, summarize_chat

ACTIVE_HANDOVER = ("Chờ tiếp nhận", "Đã tiếp nhận")


def _reason(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 255:
        raise ApiError(400, "INVALID_INPUT")
    return value.strip()


def _audit(
    transaction: Transaction,
    request: Request,
    user_id: int,
    action: str,
    handover_id: int,
    details: dict[str, Any] | None = None,
) -> None:
    transaction.execute(
        "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP,ChiTiet) VALUES(?,?,'Handover',?,?,?)",
        (
            user_id,
            action,
            handover_id,
            request.client.host if request.client else None,
            json.dumps(details, ensure_ascii=False) if details else None,
        ),
    )


def install_support_routes(app: FastAPI, database: Database, ai: AIProvider) -> None:
    @app.get("/api/chats/{chat_id}/handover")
    def customer_handover(request: Request, chat_id: str) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        row = database.fetch_one(
            "SELECT h.MaHandover id,h.LyDo reason,h.TrangThai status,h.ThoiGian createdAt,h.ThoiGianTiepNhan acceptedAt,"
            "h.ThoiGianKetThuc endedAt,h.TomTat summary,u.HoTen agentName FROM Handover h "
            "JOIN ChatSession s ON s.MaSession=h.MaSession LEFT JOIN UserAccount u ON u.MaUser=h.MaAgent "
            "WHERE h.MaSession=? AND s.MaKH=? ORDER BY h.MaHandover DESC LIMIT 1",
            (_id(chat_id), user["MaKH"]),
        )
        return {"handover": row}

    @app.post("/api/chats/{chat_id}/handover", status_code=201)
    def request_handover(
        chat_id: str,
        payload: dict[str, Any],
        request: Request,
        background: BackgroundTasks,
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        parsed_id = _id(chat_id)
        reason = _reason(payload.get("reason"))

        def work(transaction: Transaction) -> dict[str, Any]:
            chat = transaction.fetch_one(
                "SELECT TrangThai,ThoiGianKetThuc FROM ChatSession WHERE MaSession=? AND MaKH=? FOR UPDATE",
                (parsed_id, user["MaKH"]),
            )
            if not chat:
                raise ApiError(404, "CHAT_NOT_FOUND")
            if chat["TrangThai"] != "Đang hoạt động" or chat["ThoiGianKetThuc"]:
                raise ApiError(409, "CHAT_READ_ONLY")
            active = transaction.fetch_one(
                "SELECT MaHandover id,TrangThai status FROM Handover WHERE MaSession=? AND TrangThai IN ('Chờ tiếp nhận','Đã tiếp nhận') FOR UPDATE",
                (parsed_id,),
            )
            if active:
                return {"id": active["id"], "status": active["status"]}
            try:
                suggested_agent = select_agent(transaction)
                handover_id = transaction.execute(
                    "INSERT INTO Handover(MaSession,LyDo,MaAgent,TrangThai) VALUES(?,?,?,'Chờ tiếp nhận')",
                    (parsed_id, reason, suggested_agent),
                )
            except mysql.connector.errors.IntegrityError as error:
                raise ApiError(409, "HANDOVER_ACTIVE") from error
            _audit(
                transaction,
                request,
                user["MaUser"],
                "HANDOVER_REQUEST",
                handover_id,
                {"chatId": parsed_id},
            )
            return {
                "id": handover_id,
                "status": "Chờ tiếp nhận",
                "agentAvailable": suggested_agent is not None,
            }

        result = _mutate(database, request, user, {"reason": reason}, work)
        if not result.get("replayed"):
            background.add_task(summarize_chat, database, ai, parsed_id, user["MaUser"])
        return result

    @app.get("/api/handovers")
    def list_handovers(request: Request, status: str | None = None) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent", "Supervisor")
        if status and status not in {
            "Chờ tiếp nhận",
            "Đã tiếp nhận",
            "Đã kết thúc",
            "Đã hủy",
        }:
            raise ApiError(400, "INVALID_INPUT")
        scope = (
            "AND ((h.TrangThai='Chờ tiếp nhận' AND h.MaAgent IS NULL) OR h.MaAgent=?)"
            if user["TenRole"] == "Agent"
            else ""
        )
        rows = database.fetch_all(
            "SELECT h.MaHandover id,h.MaSession chatId,h.LyDo reason,h.TrangThai status,h.ThoiGian createdAt,"
            "h.ThoiGianTiepNhan acceptedAt,h.ThoiGianKetThuc endedAt,h.TomTat summary,h.MaAgent agentId,"
            "u.HoTen agentName,c.HoTen customerName,s.TieuDe title FROM Handover h JOIN ChatSession s ON s.MaSession=h.MaSession "
            "JOIN Customer c ON c.MaKH=s.MaKH LEFT JOIN UserAccount u ON u.MaUser=h.MaAgent WHERE 1=1 "
            f"{'AND h.TrangThai=? ' if status else ''}{scope} ORDER BY h.MaHandover DESC LIMIT 100",
            (*((status,) if status else ()), *((user["MaUser"],) if scope else ())),
        )
        return {"handovers": rows}

    @app.get("/api/handovers/{handover_id}")
    def handover_detail(
        request: Request, handover_id: str, before: str | None = None
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent", "Supervisor")
        parsed_id = _id(handover_id)
        cursor = _id(before) if before is not None else None
        handover = database.fetch_one(
            "SELECT h.MaHandover id,h.MaSession chatId,h.LyDo reason,h.TrangThai status,h.TomTat summary,h.MaAgent agentId,"
            "u.HoTen agentName,c.HoTen customerName,s.TieuDe title FROM Handover h JOIN ChatSession s ON s.MaSession=h.MaSession "
            "JOIN Customer c ON c.MaKH=s.MaKH LEFT JOIN UserAccount u ON u.MaUser=h.MaAgent WHERE h.MaHandover=?",
            (parsed_id,),
        )
        if not handover or (
            user["TenRole"] == "Agent"
            and handover["agentId"] not in {None, user["MaUser"]}
        ):
            raise ApiError(404, "HANDOVER_NOT_FOUND")
        messages = database.fetch_all(
            "SELECT m.MaMessage id,m.NguoiGui sender,m.NoiDung content,m.ThoiGian createdAt,a.Sentiment sentiment "
            "FROM Message m LEFT JOIN MessageAutomation a ON a.MaMessage=m.MaMessage WHERE m.MaSession=? "
            f"{'AND m.MaMessage<? ' if cursor else ''}ORDER BY m.MaMessage DESC LIMIT 51",
            (handover["chatId"], *((cursor,) if cursor else ())),
        )
        page = messages[:50]
        return {
            "handover": handover,
            "messages": list(reversed(page)),
            "next": page[-1]["id"] if len(messages) > 50 else None,
        }

    @app.post("/api/handovers/{handover_id}/accept")
    def accept_handover(request: Request, handover_id: str) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        parsed_id = _id(handover_id)
        with database.transaction() as transaction:
            handover = transaction.fetch_one(
                "SELECT MaSession,MaAgent,TrangThai FROM Handover WHERE MaHandover=? FOR UPDATE",
                (parsed_id,),
            )
            if not handover:
                raise ApiError(404, "HANDOVER_NOT_FOUND")
            if (
                handover["TrangThai"] == "Đã tiếp nhận"
                and handover["MaAgent"] == user["MaUser"]
            ):
                return {"id": parsed_id, "status": "Đã tiếp nhận", "replayed": True}
            if handover["TrangThai"] != "Chờ tiếp nhận":
                raise ApiError(409, "HANDOVER_UNAVAILABLE")
            if (
                handover["MaAgent"] is not None
                and handover["MaAgent"] != user["MaUser"]
            ):
                raise ApiError(403, "FORBIDDEN")
            transaction.execute(
                "UPDATE Handover SET MaAgent=?,TrangThai='Đã tiếp nhận',ThoiGianTiepNhan=UTC_TIMESTAMP(3) WHERE MaHandover=?",
                (user["MaUser"], parsed_id),
            )
            transaction.execute(
                "UPDATE ChatSession SET MaAgent=? WHERE MaSession=?",
                (user["MaUser"], handover["MaSession"]),
            )
            _audit(transaction, request, user["MaUser"], "HANDOVER_ACCEPT", parsed_id)
        return {"id": parsed_id, "status": "Đã tiếp nhận"}

    @app.post("/api/handovers/{handover_id}/messages", status_code=201)
    def agent_message(
        handover_id: str, payload: dict[str, Any], request: Request
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        content = payload.get("content")
        if (
            not isinstance(content, str)
            or not content.strip()
            or len(content.strip()) > 3000
        ):
            raise ApiError(400, "INVALID_INPUT")
        parsed_id = _id(handover_id)
        with database.transaction() as transaction:
            handover = transaction.fetch_one(
                "SELECT MaSession,MaAgent,TrangThai FROM Handover WHERE MaHandover=? FOR UPDATE",
                (parsed_id,),
            )
            if not handover or handover["MaAgent"] != user["MaUser"]:
                raise ApiError(404, "HANDOVER_NOT_FOUND")
            if handover["TrangThai"] != "Đã tiếp nhận":
                raise ApiError(409, "HANDOVER_READ_ONLY")
            message_id = transaction.execute(
                "INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Agent',?,?)",
                (handover["MaSession"], user["MaUser"], content.strip()),
            )
            transaction.execute(
                "UPDATE Handover SET TomTat=NULL WHERE MaHandover=?", (parsed_id,)
            )
            _audit(
                transaction,
                request,
                user["MaUser"],
                "HANDOVER_MESSAGE",
                parsed_id,
                {"messageId": message_id},
            )
        return {"id": message_id}

    @app.post("/api/handovers/{handover_id}/summary")
    def summarize_handover(
        handover_id: str, payload: dict[str, Any], request: Request
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent", "Supervisor")
        parsed_id = _id(handover_id)
        language = "en" if payload.get("language") == "en" else "vi"
        handover = database.fetch_one(
            "SELECT MaSession,MaAgent,TrangThai,TomTat FROM Handover WHERE MaHandover=?",
            (parsed_id,),
        )
        if not handover or (
            user["TenRole"] == "Agent" and handover["MaAgent"] != user["MaUser"]
        ):
            raise ApiError(404, "HANDOVER_NOT_FOUND")
        if handover["TomTat"]:
            return {"id": parsed_id, "summary": handover["TomTat"], "replayed": True}
        if not ai.enabled:
            raise ApiError(503, "AI_NOT_CONFIGURED")
        messages = database.fetch_all(
            "SELECT NguoiGui sender,NoiDung content FROM Message WHERE MaSession=? ORDER BY MaMessage",
            (handover["MaSession"],),
        )
        summary = conversation_summary(ai, messages, language)
        with database.transaction() as transaction:
            current = transaction.fetch_one(
                "SELECT TomTat FROM Handover WHERE MaHandover=? FOR UPDATE",
                (parsed_id,),
            )
            if current and current["TomTat"]:
                return {"id": parsed_id, "summary": current["TomTat"], "replayed": True}
            transaction.execute(
                "UPDATE Handover SET TomTat=?,TomTatProvider=?,TomTatModel=?,ThoiGianTomTat=UTC_TIMESTAMP(3) WHERE MaHandover=?",
                (summary, ai.provider, ai.settings.ai_chat_model, parsed_id),
            )
            _audit(transaction, request, user["MaUser"], "HANDOVER_SUMMARY", parsed_id)
        return {"id": parsed_id, "summary": summary}

    @app.post("/api/handovers/{handover_id}/finish")
    def finish_handover(
        request: Request, handover_id: str, background: BackgroundTasks
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent", "Supervisor")
        parsed_id = _id(handover_id)
        with database.transaction() as transaction:
            handover = transaction.fetch_one(
                "SELECT MaSession,MaAgent,TrangThai FROM Handover WHERE MaHandover=? FOR UPDATE",
                (parsed_id,),
            )
            if not handover or (
                user["TenRole"] == "Agent" and handover["MaAgent"] != user["MaUser"]
            ):
                raise ApiError(404, "HANDOVER_NOT_FOUND")
            if handover["TrangThai"] == "Đã kết thúc":
                return {"id": parsed_id, "status": "Đã kết thúc", "replayed": True}
            if handover["TrangThai"] != "Đã tiếp nhận":
                raise ApiError(409, "HANDOVER_UNAVAILABLE")
            transaction.execute(
                "UPDATE Handover SET TrangThai='Đã kết thúc',ThoiGianKetThuc=UTC_TIMESTAMP(3) WHERE MaHandover=?",
                (parsed_id,),
            )
            _audit(transaction, request, user["MaUser"], "HANDOVER_FINISH", parsed_id)
        background.add_task(
            summarize_chat, database, ai, handover["MaSession"], user["MaUser"]
        )
        return {"id": parsed_id, "status": "Đã kết thúc"}
