"""Recoverable demo automation. AI work never sends an Agent's reply."""

import json
import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Request
from mysql.connector.errors import IntegrityError

from backend.ai import AIProvider
from backend.auth import _require_role, current_user
from backend.db import Database, Transaction
from backend.errors import ApiError

logger = logging.getLogger(__name__)


def available_agents(transaction: Transaction) -> list[dict[str, Any]]:
    """Online means a recent authenticated heartbeat, not simply an active account."""
    return transaction.fetch_all(
        "SELECT u.MaUser FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole "
        "JOIN AgentPresence p ON p.MaUser=u.MaUser WHERE r.TenRole='Agent' AND u.TrangThai=1 "
        "AND p.LastSeen>DATE_SUB(UTC_TIMESTAMP(3),INTERVAL 2 MINUTE) "
        "AND EXISTS(SELECT 1 FROM AuthSession s WHERE s.MaUser=u.MaUser AND s.ExpiresAt>UTC_TIMESTAMP(3)) "
        "ORDER BY u.MaUser FOR UPDATE"
    )


def select_agent(
    transaction: Transaction, category_id: int | None = None
) -> int | None:
    agents = available_agents(transaction)
    if not agents:
        return None
    loads = []
    for agent in agents:
        load = (
            transaction.fetch_one(
                "SELECT COUNT(*) total,SUM(MaCategory<=>?) sameCategory FROM Ticket "
                "WHERE MaAgent=? AND TrangThai<>'Đã đóng'",
                (category_id, agent["MaUser"]),
            )
            or {}
        )
        loads.append(
            (
                int(load.get("total") or 0),
                int(load.get("sameCategory") or 0),
                int(agent["MaUser"]),
            )
        )
    return min(loads)[2]


def _alert(
    transaction: Transaction, source: str, identifier: int, sentiment: str
) -> None:
    if sentiment == "Bức xúc cao":
        transaction.execute(
            "INSERT IGNORE INTO SupervisorAlert(SourceType,SourceId,Sentiment) VALUES(?,?,'Bức xúc cao')",
            (source, identifier),
        )


def _audit(
    transaction: Transaction, actor: int, action: str, target: str, identifier: int
) -> None:
    transaction.execute(
        "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong) VALUES(?,?,?,?)",
        (actor, action, target, identifier),
    )


def automate_ticket(
    database: Database, ai: AIProvider, ticket_id: int, actor: int
) -> None:
    if not ai.enabled or not callable(getattr(ai, "classify_context", None)):
        return
    try:
        ticket = database.fetch_one(
            "SELECT TieuDe,NoiDung,TrangThai FROM Ticket WHERE MaTicket=?", (ticket_id,)
        )
        if not ticket or ticket["TrangThai"] != "Mới":
            return
        categories = database.fetch_all(
            "SELECT MaCategory,TenCategory FROM TicketCategory ORDER BY MaCategory"
        )
        result = ai.classify_context(
            ticket["TieuDe"] + "\n" + ticket["NoiDung"],
            [row["TenCategory"] for row in categories],
        )
        category_id = next(
            (
                row["MaCategory"]
                for row in categories
                if row["TenCategory"] == result["category"]
            ),
            None,
        )
        with database.transaction() as transaction:
            current = transaction.fetch_one(
                "SELECT TieuDe,NoiDung,TrangThai,MaAgent FROM Ticket WHERE MaTicket=? FOR UPDATE",
                (ticket_id,),
            )
            old = transaction.fetch_one(
                "SELECT State FROM TicketAutomation WHERE MaTicket=? FOR UPDATE",
                (ticket_id,),
            )
            if old and old["State"] == "Done":
                return
            transaction.execute(
                "INSERT IGNORE INTO TicketAutomation(MaTicket) VALUES(?)", (ticket_id,)
            )
            if (
                not current
                or current["TrangThai"] != "Mới"
                or current["MaAgent"] is not None
                or current["TieuDe"] != ticket["TieuDe"]
                or current["NoiDung"] != ticket["NoiDung"]
            ):
                transaction.execute(
                    "UPDATE TicketAutomation SET State='Stale',UpdatedAt=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                    (ticket_id,),
                )
                return
            agent_id = select_agent(transaction, category_id)
            transaction.execute(
                "UPDATE Ticket SET MaCategory=?,MucDoUuTien=?,MaAgent=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                (category_id, result["priority"], agent_id, ticket_id),
            )
            if agent_id is not None:
                transaction.execute(
                    "INSERT INTO TicketAssignmentHistory(MaTicket,MaAgentCu,MaAgentMoi,MaNguoiThucHien) VALUES(?,NULL,?,?)",
                    (ticket_id, agent_id, actor),
                )
            transaction.execute(
                "UPDATE TicketAutomation SET State='Done',Category=?,Priority=?,Sentiment=?,UpdatedAt=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                (
                    result["category"],
                    result["priority"],
                    result["sentiment"],
                    ticket_id,
                ),
            )
            _alert(transaction, "Ticket", ticket_id, result["sentiment"])
            _audit(transaction, actor, "TICKET_AUTO_CLASSIFY", "Ticket", ticket_id)
    except Exception:
        logger.warning(
            "Ticket automation unavailable; ticket retained for manual handling"
        )
        try:
            database.execute(
                "INSERT INTO TicketAutomation(MaTicket,State) VALUES(?,'Failed') "
                "ON DUPLICATE KEY UPDATE State=IF(State='Done',State,'Failed'),UpdatedAt=UTC_TIMESTAMP(3)",
                (ticket_id,),
            )
        except Exception:
            logger.warning("Could not persist automation retry state")


def analyze_message(
    database: Database, ai: AIProvider, message_id: int, actor: int
) -> None:
    if not ai.enabled or not callable(getattr(ai, "classify_context", None)):
        return
    try:
        row = database.fetch_one(
            "SELECT NoiDung FROM Message WHERE MaMessage=? AND NguoiGui='Customer'",
            (message_id,),
        )
        if not row:
            return
        result = ai.classify_context(row["NoiDung"], ["Hỗ trợ khách hàng"])
        with database.transaction() as transaction:
            # Serialize retries through the source Message, without holding locks during AI calls.
            transaction.fetch_one(
                "SELECT MaMessage FROM Message WHERE MaMessage=? FOR UPDATE",
                (message_id,),
            )
            old = transaction.fetch_one(
                "SELECT State FROM MessageAutomation WHERE MaMessage=? FOR UPDATE",
                (message_id,),
            )
            if old and old["State"] == "Done":
                return
            transaction.execute(
                "INSERT INTO SentimentAnalysis(MaMessage,CamXuc) VALUES(?,?)",
                (message_id, result["sentiment"]),
            )
            transaction.execute(
                "INSERT INTO MessageAutomation(MaMessage,State,Sentiment) VALUES(?,'Done',?) "
                "ON DUPLICATE KEY UPDATE State='Done',Sentiment=VALUES(Sentiment),UpdatedAt=UTC_TIMESTAMP(3)",
                (message_id, result["sentiment"]),
            )
            _alert(transaction, "Message", message_id, result["sentiment"])
            _audit(transaction, actor, "MESSAGE_SENTIMENT", "Message", message_id)
    except Exception:
        logger.warning("Sentiment service unavailable; message retained")
        try:
            database.execute(
                "INSERT INTO MessageAutomation(MaMessage,State) VALUES(?,'Failed') "
                "ON DUPLICATE KEY UPDATE State=IF(State='Done',State,'Failed')",
                (message_id,),
            )
        except Exception:
            logger.warning("Could not persist sentiment retry state")


def conversation_summary(
    ai: AIProvider, messages: list[dict[str, Any]], language: str
) -> str:
    """Hierarchical summarization covers the full history without exceeding provider input limits."""
    while len(messages) > 200:
        messages = [
            {
                "sender": "Summary",
                "content": ai.summarize_conversation(messages[i : i + 200], language),
            }
            for i in range(0, len(messages), 200)
        ]
    return ai.summarize_conversation(messages, language)


def summarize_chat(
    database: Database, ai: AIProvider, chat_id: int, actor: int, language: str = "vi"
) -> None:
    if not ai.enabled or not callable(getattr(ai, "summarize_conversation", None)):
        return
    try:
        messages = database.fetch_all(
            "SELECT NguoiGui sender,NoiDung content FROM Message WHERE MaSession=? ORDER BY MaMessage",
            (chat_id,),
        )
        if not messages:
            return
        summary = conversation_summary(ai, messages, language)
        with database.transaction() as transaction:
            transaction.fetch_one(
                "SELECT MaSession FROM ChatSession WHERE MaSession=? FOR UPDATE",
                (chat_id,),
            )
            transaction.execute(
                "INSERT INTO ConversationSummary(MaSession,NoiDungTomTat) VALUES(?,?)",
                (chat_id, summary),
            )
            transaction.execute(
                "UPDATE Handover SET TomTat=?,TomTatProvider=?,ThoiGianTomTat=UTC_TIMESTAMP(3) "
                "WHERE MaSession=? ORDER BY MaHandover DESC LIMIT 1",
                (summary, ai.provider, chat_id),
            )
            _audit(transaction, actor, "CHAT_AUTO_SUMMARY", "ChatSession", chat_id)
    except Exception:
        logger.warning("Automatic summary unavailable; support remains available")


def install_automation_routes(app: FastAPI, database: Database, ai: AIProvider) -> None:
    @app.post("/api/presence")
    def heartbeat(request: Request, payload: dict[str, Any]) -> dict[str, str]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        database.execute(
            "INSERT INTO AgentPresence(MaUser) VALUES(?) ON DUPLICATE KEY UPDATE LastSeen=UTC_TIMESTAMP(3)",
            (user["MaUser"],),
        )
        return {"status": "online"}

    @app.get("/api/supervisor/alerts")
    def alerts(request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        return {
            "alerts": database.fetch_all(
                "SELECT a.MaAlert id,a.SourceType source,a.SourceId sourceId,a.Sentiment sentiment,a.CreatedAt createdAt,"
                "t.MaTicket ticketId,COALESCE(m.MaSession,t.MaSession) chatId FROM SupervisorAlert a "
                "LEFT JOIN Ticket t ON a.SourceType='Ticket' AND t.MaTicket=a.SourceId "
                "LEFT JOIN Message m ON a.SourceType='Message' AND m.MaMessage=a.SourceId "
                "WHERE a.AcknowledgedAt IS NULL ORDER BY a.MaAlert DESC LIMIT 100"
            )
        }

    @app.post("/api/supervisor/alerts/{alert_id}/acknowledge")
    def acknowledge(
        alert_id: int, request: Request, payload: dict[str, Any]
    ) -> dict[str, int]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        with database.transaction() as transaction:
            if not transaction.fetch_one(
                "SELECT MaAlert FROM SupervisorAlert WHERE MaAlert=? FOR UPDATE",
                (alert_id,),
            ):
                raise ApiError(404, "ALERT_NOT_FOUND")
            transaction.execute(
                "UPDATE SupervisorAlert SET AcknowledgedBy=?,AcknowledgedAt=UTC_TIMESTAMP(3) WHERE MaAlert=? AND AcknowledgedAt IS NULL",
                (user["MaUser"], alert_id),
            )
            _audit(
                transaction,
                user["MaUser"],
                "ALERT_ACKNOWLEDGE",
                "SupervisorAlert",
                alert_id,
            )
        return {"id": alert_id}

    @app.post("/api/tickets/{ticket_id}/automation/retry")
    def retry_ticket(
        ticket_id: int,
        request: Request,
        payload: dict[str, Any],
        background: BackgroundTasks,
    ) -> dict[str, str]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        if not database.fetch_one(
            "SELECT MaTicket FROM Ticket WHERE MaTicket=?", (ticket_id,)
        ):
            raise ApiError(404, "TICKET_NOT_FOUND")
        background.add_task(automate_ticket, database, ai, ticket_id, user["MaUser"])
        return {"status": "scheduled"}

    @app.get("/api/supervisor/automation")
    def pending_automation(request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        return {
            "tickets": database.fetch_all(
                "SELECT t.MaTicket id,t.TieuDe title,COALESCE(a.State,'Pending') state "
                "FROM Ticket t LEFT JOIN TicketAutomation a ON a.MaTicket=t.MaTicket "
                "WHERE t.TrangThai='Mới' AND t.MaAgent IS NULL AND (a.State IS NULL OR a.State<>'Done') "
                "ORDER BY t.MaTicket DESC LIMIT 50"
            )
        }

    @app.post("/api/chats/{chat_id}/evaluation", status_code=201)
    def rate_chat(
        chat_id: int, payload: dict[str, Any], request: Request
    ) -> dict[str, int]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        stars, comment = payload.get("stars"), payload.get("comment", "")
        if (
            type(stars) is not int
            or not 1 <= stars <= 5
            or not isinstance(comment, str)
            or len(comment) > 1000
        ):
            raise ApiError(400, "INVALID_INPUT")
        try:
            with database.transaction() as transaction:
                chat = transaction.fetch_one(
                    "SELECT ThoiGianKetThuc FROM ChatSession WHERE MaSession=? AND MaKH=? FOR UPDATE",
                    (chat_id, user["MaKH"]),
                )
                if not chat:
                    raise ApiError(404, "CHAT_NOT_FOUND")
                if not chat["ThoiGianKetThuc"]:
                    raise ApiError(409, "CHAT_NOT_CLOSED")
                identifier = transaction.execute(
                    "INSERT INTO Evaluation(MaKH,MaSession,SoSao,NhanXet) VALUES(?,?,?,?)",
                    (user["MaKH"], chat_id, stars, comment.strip()),
                )
                _audit(
                    transaction,
                    user["MaUser"],
                    "CHAT_EVALUATION",
                    "ChatSession",
                    chat_id,
                )
            return {"id": identifier}
        except IntegrityError as error:
            if error.errno == 1062:
                raise ApiError(409, "ALREADY_EVALUATED") from error
            raise
