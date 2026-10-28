import hashlib
import json
import re
from datetime import date
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.auth import _require_role, current_user
from backend.ai import AIProvider
from backend.db import Database, Transaction
from backend.errors import ApiError


STAGES = ("Mới", "Đang xử lý", "Chờ khách hàng", "Đã đóng")
PRIORITIES = ("Thấp", "Trung bình", "Cao", "Khẩn cấp")
FIELDS = (
    "t.MaTicket id,t.MaKH customerId,t.MaAgent agentId,t.TieuDe title,t.TrangThai status,"
    "t.MucDoUuTien priority,t.MaCategory categoryId,t.NgayTao createdAt,t.NgayCapNhat updatedAt,t.NgayDong closedAt"
)
KEY_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def numeric_id(value: str | int) -> int:
    raw = str(value)
    if not re.fullmatch(r"[1-9]\d{0,9}", raw) or int(raw) > 2147483647:
        raise ApiError(400, "INVALID_INPUT")
    return int(raw)


def text_value(value: object, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ApiError(400, "INVALID_INPUT")
    return value.strip()


def evaluation_values(payload: dict[str, Any]) -> tuple[int, str | None]:
    stars = payload.get("stars")
    comment = payload.get("comment", "")
    if type(stars) is not int or not 1 <= stars <= 5 or not isinstance(comment, str) or len(comment.strip()) > 1000:
        raise ApiError(400, "INVALID_INPUT")
    return stars, comment.strip() or None


def next_status(current: str, target: str) -> bool:
    return (current, target) in {
        ("Mới", "Đang xử lý"),
        ("Đang xử lý", "Chờ khách hàng"),
        ("Chờ khách hàng", "Đang xử lý"),
        ("Đang xử lý", "Đã đóng"),
        ("Chờ khách hàng", "Đã đóng"),
    }


def can_claim(agent_id: int | None, status: str, requesting_agent_id: int | None = None) -> bool:
    return status == STAGES[0] and (agent_id is None or agent_id == requesting_agent_id)


def visibility(user: dict[str, Any]) -> tuple[str, tuple[object, ...]]:
    if user["TenRole"] == "Customer":
        return "t.MaKH=?", (user["MaKH"],)
    if user["TenRole"] == "Agent":
        return "(t.MaAgent=? OR (t.MaAgent IS NULL AND t.TrangThai='Mới'))", (user["MaUser"],)
    return "1=1", ()


def _ticket_code(ticket_id: int) -> str:
    return f"TK-{ticket_id:06d}"


def _require_key(request: Request) -> str:
    key = request.headers.get("idempotency-key", "")
    if not KEY_PATTERN.fullmatch(key):
        raise ApiError(400, "REQUEST_KEY_REQUIRED")
    return key


def _payload_hash(path: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps([path, payload], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _mutate(
    database: Database,
    request: Request,
    user: dict[str, Any],
    payload: dict[str, Any],
    work: Callable[[Transaction], dict[str, Any]],
) -> dict[str, Any]:
    key = _require_key(request)
    request_hash = _payload_hash(request.url.path, payload)
    with database.transaction() as transaction:
        actor = transaction.fetch_one("SELECT TrangThai FROM UserAccount WHERE MaUser=? FOR UPDATE", (user["MaUser"],))
        if not actor or not actor["TrangThai"]:
            raise ApiError(401, "UNAUTHENTICATED")
        old = transaction.fetch_one(
            "SELECT RequestHash,Result FROM TicketRequest WHERE MaUser=? AND RequestKey=?",
            (user["MaUser"], key),
        )
        if old:
            if old["RequestHash"] != request_hash:
                raise ApiError(409, "REQUEST_KEY_CONFLICT")
            result = old["Result"]
            if isinstance(result, str):
                result = json.loads(result)
            return {**result, "replayed": True}
        result = work(transaction)
        transaction.execute(
            "INSERT INTO TicketRequest(MaUser,RequestKey,RequestHash,Result) VALUES(?,?,?,?)",
            (user["MaUser"], key, request_hash, json.dumps(result, ensure_ascii=False, separators=(",", ":"))),
        )
        return result


def _event(
    transaction: Transaction,
    request: Request,
    user_id: int,
    ticket_id: int,
    action: str,
    previous: str | None = None,
    target: str | None = None,
) -> None:
    if target:
        transaction.execute(
            "INSERT INTO TicketStatusHistory(MaTicket,TrangThaiCu,TrangThaiMoi,MaUser) VALUES(?,?,?,?)",
            (ticket_id, previous, target, user_id),
        )
    transaction.execute(
        "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'Ticket',?,?)",
        (user_id, action, ticket_id, request.client.host if request.client else None),
    )


def _accessible(transaction: Transaction, user: dict[str, Any], ticket_id: int, lock: bool = False) -> dict[str, Any]:
    where, parameters = visibility(user)
    suffix = " FOR UPDATE" if lock else ""
    ticket = transaction.fetch_one(
        f"SELECT {FIELDS},t.NoiDung content FROM Ticket t WHERE t.MaTicket=? AND {where}{suffix}",
        (ticket_id, *parameters),
    )
    if not ticket:
        raise ApiError(404, "TICKET_NOT_FOUND")
    ticket["code"] = _ticket_code(ticket["id"])
    return ticket


def install_ticket_routes(
    app: FastAPI,
    database: Database,
    ai: AIProvider | None = None,
    provider: str = "",
    model: str = "",
) -> None:
    @app.get("/api/tickets")
    def list_tickets(
        request: Request,
        before: str | None = None,
        status: str | None = None,
        customer: str | None = None,
        priority: str | None = None,
        startDate: str | None = None,
        endDate: str | None = None,
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer", "Agent", "Supervisor")
        cursor = numeric_id(before) if before is not None else 2147483647
        if status is not None and status not in STAGES:
            raise ApiError(400, "INVALID_INPUT")
        if priority is not None and priority not in PRIORITIES:
            raise ApiError(400, "INVALID_INPUT")
        customer = customer.strip() if isinstance(customer, str) else None
        if customer is not None and (not customer or len(customer) > 100):
            raise ApiError(400, "INVALID_INPUT")
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if startDate is not None and not date_pattern.fullmatch(startDate):
            raise ApiError(400, "INVALID_INPUT")
        if endDate is not None and not date_pattern.fullmatch(endDate):
            raise ApiError(400, "INVALID_INPUT")
        try:
            for value in (startDate, endDate):
                if value is not None:
                    date.fromisoformat(value)
        except ValueError as error:
            raise ApiError(400, "INVALID_INPUT") from error
        if startDate and endDate and startDate > endDate:
            raise ApiError(400, "INVALID_INPUT")
        where, parameters = visibility(user)
        filters = [where, "t.MaTicket<?"]
        values: list[object] = [*parameters, cursor]
        if status:
            filters.append("t.TrangThai=?")
            values.append(status)
        if priority:
            filters.append("t.MucDoUuTien=?")
            values.append(priority)
        if customer:
            filters.append("(c.HoTen LIKE ? OR c.Email LIKE ? OR c.SoDienThoai LIKE ?)")
            search = f"%{customer}%"
            values.extend((search, search, search))
        if startDate:
            filters.append("t.NgayTao>=?")
            values.append(startDate)
        if endDate:
            filters.append("t.NgayTao<DATE_ADD(?,INTERVAL 1 DAY)")
            values.append(endDate)
        rows = database.fetch_all(
            f"SELECT {FIELDS} FROM Ticket t JOIN Customer c ON c.MaKH=t.MaKH "
            f"WHERE {' AND '.join(filters)} ORDER BY t.MaTicket DESC LIMIT 31",
            tuple(values),
        )
        more = len(rows) > 30
        tickets = rows[:30]
        for ticket in tickets:
            ticket["code"] = _ticket_code(ticket["id"])
        return {"tickets": tickets, "next": tickets[-1]["id"] if more else None}

    @app.get("/api/tickets/categories")
    def list_categories(request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent", "Supervisor")
        return {"categories": database.fetch_all("SELECT MaCategory id,TenCategory name FROM TicketCategory ORDER BY TenCategory")}

    @app.get("/api/tickets/agents")
    def list_assignable_agents(request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        agents = database.fetch_all(
            "SELECT u.MaUser id,u.HoTen name,u.Email email FROM UserAccount u "
            "JOIN Role r ON r.MaRole=u.MaRole WHERE r.TenRole='Agent' AND u.TrangThai=1 ORDER BY u.HoTen,u.MaUser LIMIT 200"
        )
        return {"agents": agents}

    @app.get("/api/tickets/{ticket_id}")
    def ticket_detail(ticket_id: str, request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer", "Agent", "Supervisor")
        parsed_id = numeric_id(ticket_id)
        with database.transaction() as transaction:
            ticket = _accessible(transaction, user, parsed_id)
            replies = transaction.fetch_all(
                "SELECT r.MaReply id,r.MaUser userId,u.HoTen author,role.TenRole role,r.NoiDung content,r.ThoiGian createdAt "
                "FROM TicketReply r JOIN UserAccount u ON u.MaUser=r.MaUser JOIN Role role ON role.MaRole=u.MaRole "
                "WHERE r.MaTicket=? ORDER BY r.MaReply",
                (parsed_id,),
            )
            history = transaction.fetch_all(
                "SELECT h.MaHistory id,h.TrangThaiCu previous,h.TrangThaiMoi status,u.HoTen author,h.ThoiGian createdAt "
                "FROM TicketStatusHistory h JOIN UserAccount u ON u.MaUser=h.MaUser WHERE h.MaTicket=? ORDER BY h.MaHistory",
                (parsed_id,),
            )
            assignments = transaction.fetch_all(
                "SELECT h.MaAssignment id,previous.HoTen previousAgent,assigned.HoTen agent,actor.HoTen performedBy,"
                "h.ThoiGian createdAt FROM TicketAssignmentHistory h "
                "LEFT JOIN UserAccount previous ON previous.MaUser=h.MaAgentCu "
                "JOIN UserAccount assigned ON assigned.MaUser=h.MaAgentMoi "
                "JOIN UserAccount actor ON actor.MaUser=h.MaNguoiThucHien WHERE h.MaTicket=? ORDER BY h.MaAssignment",
                (parsed_id,),
            ) if user["TenRole"] in {"Agent", "Supervisor"} else []
            evaluation = transaction.fetch_one(
                "SELECT MaDanhGia id,SoSao stars,NhanXet comment,NgayDanhGia createdAt FROM Evaluation WHERE MaTicket=? AND MaKH=?",
                (parsed_id, user["MaKH"] if user["TenRole"] == "Customer" else ticket["customerId"]),
            )
            analyses = transaction.fetch_all(
                "SELECT MaAnalysis id,CategorySuggestion category,PrioritySuggestion priority,"
                "SentimentSuggestion sentiment,DraftReply draftReply,Summary summary,ReviewStatus status "
                "FROM TicketAIAnalysis WHERE MaTicket=? ORDER BY MaAnalysis DESC LIMIT 10",
                (parsed_id,),
            ) if user["TenRole"] in {"Agent", "Supervisor"} else []
        return {"ticket": ticket, "replies": replies, "history": history, "assignments": assignments,
                "evaluation": evaluation, "analyses": analyses}

    @app.post("/api/tickets/{ticket_id}/details")
    def update_details(ticket_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent", "Supervisor")
        parsed_id = numeric_id(ticket_id)
        if payload.keys() - {"title", "content", "categoryId"}:
            raise ApiError(400, "INVALID_INPUT")
        title, content = text_value(payload.get("title"), 200), text_value(payload.get("content"), 3000)
        category_id = numeric_id(payload["categoryId"]) if payload.get("categoryId") is not None else None

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = _accessible(transaction, user, parsed_id, lock=True)
            if ticket["status"] == STAGES[3]:
                raise ApiError(409, "TICKET_READ_ONLY")
            if user["TenRole"] == "Agent" and (ticket["agentId"] != user["MaUser"] or ticket["status"] == STAGES[0]):
                raise ApiError(403, "CLAIM_REQUIRED")
            if category_id is not None and not transaction.fetch_one(
                "SELECT MaCategory FROM TicketCategory WHERE MaCategory=?", (category_id,)
            ):
                raise ApiError(400, "INVALID_INPUT")
            transaction.execute(
                "UPDATE Ticket SET TieuDe=?,NoiDung=?,MaCategory=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                (title, content, category_id, parsed_id),
            )
            _event(transaction, request, user["MaUser"], parsed_id, "TICKET_DETAILS")
            return {"id": parsed_id}

        return _mutate(database, request, user, {"title": title, "content": content, "categoryId": category_id}, work)

    @app.post("/api/tickets", status_code=201)
    def create_ticket(payload: dict[str, Any], request: Request) -> JSONResponse:
        user = current_user(request, database)
        _require_role(user, "Customer")
        title = text_value(payload.get("title"), 200)
        content = text_value(payload.get("content"), 2000)
        priority = payload.get("priority", "Trung bình")
        if priority not in PRIORITIES:
            raise ApiError(400, "INVALID_INPUT")
        body = {"title": title, "content": content, "priority": priority}

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket_id = transaction.execute(
                "INSERT INTO Ticket(MaKH,TieuDe,NoiDung,MucDoUuTien) VALUES(?,?,?,?)",
                (user["MaKH"], title, content, priority),
            )
            _event(transaction, request, user["MaUser"], ticket_id, "TICKET_CREATE", None, STAGES[0])
            return {"id": ticket_id, "code": _ticket_code(ticket_id)}

        result = _mutate(database, request, user, body, work)
        return JSONResponse(result, status_code=200 if result.get("replayed") else 201)

    @app.post("/api/tickets/{ticket_id}/claim")
    def claim_ticket(ticket_id: str, request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        parsed_id = numeric_id(ticket_id)

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = transaction.fetch_one("SELECT MaAgent,TrangThai FROM Ticket WHERE MaTicket=? FOR UPDATE", (parsed_id,))
            if not ticket:
                raise ApiError(404, "TICKET_NOT_FOUND")
            if not can_claim(ticket["MaAgent"], ticket["TrangThai"], user["MaUser"]):
                raise ApiError(409, "TICKET_ALREADY_CLAIMED")
            was_unassigned = ticket["MaAgent"] is None
            transaction.execute(
                "UPDATE Ticket SET MaAgent=?,TrangThai='Đang xử lý',NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                (user["MaUser"], parsed_id),
            )
            if was_unassigned:
                transaction.execute(
                    "INSERT INTO TicketAssignmentHistory(MaTicket,MaAgentCu,MaAgentMoi,MaNguoiThucHien) VALUES(?,?,?,?)",
                    (parsed_id, None, user["MaUser"], user["MaUser"]),
                )
            _event(transaction, request, user["MaUser"], parsed_id, "TICKET_CLAIM", STAGES[0], STAGES[1])
            return {"id": parsed_id}

        return _mutate(database, request, user, {}, work)

    @app.post("/api/tickets/{ticket_id}/assign")
    def assign_ticket(ticket_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        parsed_id = numeric_id(ticket_id)
        agent_id = numeric_id(payload.get("agentId"))
        body = {"agentId": agent_id}

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = _accessible(transaction, user, parsed_id, lock=True)
            if ticket["status"] not in STAGES[:3]:
                raise ApiError(409, "TICKET_READ_ONLY")
            agent = transaction.fetch_one(
                "SELECT u.MaUser FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole "
                "WHERE u.MaUser=? AND r.TenRole='Agent' AND u.TrangThai=1 FOR UPDATE",
                (agent_id,),
            )
            if not agent:
                raise ApiError(400, "AGENT_NOT_AVAILABLE")
            if ticket["agentId"] != agent_id:
                transaction.execute(
                    "UPDATE Ticket SET MaAgent=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                    (agent_id, parsed_id),
                )
                transaction.execute(
                    "INSERT INTO TicketAssignmentHistory(MaTicket,MaAgentCu,MaAgentMoi,MaNguoiThucHien) VALUES(?,?,?,?)",
                    (parsed_id, ticket["agentId"], agent_id, user["MaUser"]),
                )
                _event(transaction, request, user["MaUser"], parsed_id, "TICKET_ASSIGN")
            return {"id": parsed_id, "agentId": agent_id, "status": ticket["status"]}

        return _mutate(database, request, user, body, work)

    @app.post("/api/tickets/{ticket_id}/replies")
    def add_reply(ticket_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer", "Agent")
        parsed_id = numeric_id(ticket_id)
        content = text_value(payload.get("content"), 2000)

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = _accessible(transaction, user, parsed_id, lock=True)
            if user["TenRole"] == "Agent" and ticket["agentId"] != user["MaUser"]:
                raise ApiError(403, "CLAIM_REQUIRED")
            if ticket["status"] not in STAGES[:3]:
                raise ApiError(409, "TICKET_READ_ONLY")
            reply_id = transaction.execute(
                "INSERT INTO TicketReply(MaTicket,MaUser,NoiDung) VALUES(?,?,?)",
                (parsed_id, user["MaUser"], content),
            )
            transaction.execute("UPDATE Ticket SET NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?", (parsed_id,))
            _event(transaction, request, user["MaUser"], parsed_id, "TICKET_REPLY")
            if user["TenRole"] == "Customer" and ticket["status"] == "Chờ khách hàng":
                transaction.execute(
                    "UPDATE Ticket SET TrangThai='Đang xử lý',NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                    (parsed_id,),
                )
                _event(transaction, request, user["MaUser"], parsed_id, "TICKET_STATUS", "Chờ khách hàng", "Đang xử lý")
            return {"id": parsed_id, "replyId": reply_id}

        return _mutate(database, request, user, {"content": content}, work)

    @app.post("/api/tickets/{ticket_id}/status")
    def update_status(ticket_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        parsed_id = numeric_id(ticket_id)
        target = payload.get("status")
        if target not in STAGES[1:]:
            raise ApiError(400, "INVALID_INPUT")

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = _accessible(transaction, user, parsed_id, lock=True)
            if ticket["agentId"] != user["MaUser"]:
                raise ApiError(403, "CLAIM_REQUIRED")
            if not next_status(ticket["status"], target):
                raise ApiError(409, "INVALID_TRANSITION")
            if target == "Đã đóng" and not transaction.fetch_one(
                "SELECT MaReply FROM TicketReply WHERE MaTicket=? AND MaUser=? LIMIT 1",
                (parsed_id, user["MaUser"]),
            ):
                raise ApiError(409, "REPLY_REQUIRED")
            transaction.execute(
                "UPDATE Ticket SET TrangThai=?,NgayCapNhat=UTC_TIMESTAMP(3),"
                "NgayDong=IF(?='Đã đóng',UTC_TIMESTAMP(3),NULL) WHERE MaTicket=?",
                (target, target, parsed_id),
            )
            _event(transaction, request, user["MaUser"], parsed_id, "TICKET_STATUS", ticket["status"], target)
            return {"id": parsed_id}

        return _mutate(database, request, user, {"status": target}, work)

    @app.post("/api/tickets/{ticket_id}/priority")
    def update_priority(ticket_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        parsed_id = numeric_id(ticket_id)
        priority = payload.get("priority")
        if priority not in PRIORITIES:
            raise ApiError(400, "INVALID_INPUT")

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = _accessible(transaction, user, parsed_id, lock=True)
            if ticket["agentId"] != user["MaUser"]:
                raise ApiError(403, "CLAIM_REQUIRED")
            if ticket["status"] not in STAGES[1:3]:
                raise ApiError(409, "TICKET_READ_ONLY")
            transaction.execute(
                "UPDATE Ticket SET MucDoUuTien=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?",
                (priority, parsed_id),
            )
            _event(transaction, request, user["MaUser"], parsed_id, "TICKET_PRIORITY")
            return {"id": parsed_id}

        return _mutate(database, request, user, {"priority": priority}, work)

    @app.post("/api/tickets/{ticket_id}/evaluation", status_code=201)
    def create_evaluation(ticket_id: str, payload: dict[str, Any], request: Request) -> JSONResponse:
        user = current_user(request, database)
        _require_role(user, "Customer")
        parsed_id = numeric_id(ticket_id)
        stars, comment = evaluation_values(payload)
        body = {"stars": stars, "comment": comment}

        def work(transaction: Transaction) -> dict[str, Any]:
            ticket = _accessible(transaction, user, parsed_id, lock=True)
            if ticket["status"] != STAGES[3]:
                raise ApiError(409, "TICKET_NOT_CLOSED")
            old = transaction.fetch_one("SELECT MaDanhGia FROM Evaluation WHERE MaTicket=?", (parsed_id,))
            if old:
                raise ApiError(409, "EVALUATION_EXISTS")
            evaluation_id = transaction.execute(
                "INSERT INTO Evaluation(MaKH,MaTicket,SoSao,NhanXet) VALUES(?,?,?,?)",
                (user["MaKH"], parsed_id, stars, comment),
            )
            _event(transaction, request, user["MaUser"], parsed_id, "TICKET_EVALUATION")
            return {"id": evaluation_id, "ticketId": parsed_id, "stars": stars}

        result = _mutate(database, request, user, body, work)
        return JSONResponse(result, status_code=200 if result.get("replayed") else 201)

    @app.post("/api/tickets/{ticket_id}/ai-assist", status_code=201)
    def create_ai_assist(ticket_id: str, payload: dict[str, Any], request: Request) -> JSONResponse:
        user = current_user(request, database)
        _require_role(user, "Agent")
        parsed_id = numeric_id(ticket_id)
        language = "en" if payload.get("language") == "en" else "vi"
        body = {"language": language}
        key = _require_key(request)
        request_hash = _payload_hash(request.url.path, body)
        existing = database.fetch_one(
            "SELECT MaAnalysis id,RequestHash,CategorySuggestion category,PrioritySuggestion priority,SentimentSuggestion sentiment,"
            "DraftReply draftReply,Summary summary,ReviewStatus status,Provider aiProvider "
            "FROM TicketAIAnalysis WHERE MaUser=? AND RequestKey=?",
            (user["MaUser"], key),
        )
        if existing:
            if existing["RequestHash"] != request_hash:
                raise ApiError(409, "REQUEST_KEY_CONFLICT")
            existing.pop("RequestHash")
            if existing["status"] not in {"Pending", "Selected", "Dismissed"}:
                raise ApiError(503, "AI_UNAVAILABLE")
            return JSONResponse({**existing, "replayed": True, "requiresHumanReview": True}, status_code=200)
        if ai is None or not ai.enabled:
            raise ApiError(503, "AI_NOT_CONFIGURED")

        ticket = database.fetch_one(
            f"SELECT {FIELDS},t.NoiDung content,t.MaSession sessionId FROM Ticket t WHERE t.MaTicket=? AND t.MaAgent=?",
            (parsed_id, user["MaUser"]),
        )
        if not ticket:
            raise ApiError(404, "TICKET_NOT_FOUND")
        if ticket["status"] != STAGES[1]:
            raise ApiError(409, "TICKET_READ_ONLY")
        replies = database.fetch_all(
            "SELECT role.TenRole role,r.NoiDung content FROM TicketReply r "
            "JOIN UserAccount u ON u.MaUser=r.MaUser JOIN Role role ON role.MaRole=u.MaRole "
            "WHERE r.MaTicket=? ORDER BY r.MaReply DESC LIMIT 10",
            (parsed_id,),
        )
        chat_messages = database.fetch_all(
            "SELECT NguoiGui sender,NoiDung content FROM Message WHERE MaSession=? ORDER BY MaMessage DESC LIMIT 20",
            (ticket["sessionId"],),
        ) if ticket["sessionId"] else []
        categories = database.fetch_all("SELECT TenCategory name FROM TicketCategory ORDER BY MaCategory LIMIT 50")
        suggestions = ai.support_assist(
            {
                "ticket": {"title": ticket["title"], "content": ticket["content"], "priority": ticket["priority"]},
                "recent_replies": list(reversed(replies)),
                "conversation_history": list(reversed(chat_messages)),
                "available_categories": [row["name"] for row in categories],
            },
            language,
        )
        with database.transaction() as transaction:
            current = transaction.fetch_one(
                "SELECT MaAgent,TrangThai FROM Ticket WHERE MaTicket=? FOR UPDATE",
                (parsed_id,),
            )
            if not current or current["MaAgent"] != user["MaUser"]:
                raise ApiError(409, "CLAIM_REQUIRED")
            if current["TrangThai"] != STAGES[1]:
                raise ApiError(409, "TICKET_READ_ONLY")
            raced = transaction.fetch_one(
                "SELECT MaAnalysis id,RequestHash,CategorySuggestion category,PrioritySuggestion priority,"
                "SentimentSuggestion sentiment,DraftReply draftReply,Summary summary,ReviewStatus status,Provider aiProvider "
                "FROM TicketAIAnalysis WHERE MaUser=? AND RequestKey=? FOR UPDATE",
                (user["MaUser"], key),
            )
            if raced:
                if raced["RequestHash"] != request_hash:
                    raise ApiError(409, "REQUEST_KEY_CONFLICT")
                result = {name: value for name, value in raced.items() if name != "RequestHash"}
                return JSONResponse({**result, "replayed": True, "requiresHumanReview": True}, status_code=200)
            analysis_id = transaction.execute(
                "INSERT INTO TicketAIAnalysis(MaTicket,MaUser,RequestKey,RequestHash,CategorySuggestion,PrioritySuggestion,"
                "SentimentSuggestion,DraftReply,Summary,Provider,Model) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    parsed_id,
                    user["MaUser"],
                    key,
                    request_hash,
                    suggestions["category"],
                    suggestions["priority"],
                    suggestions["sentiment"],
                    suggestions["draftReply"],
                    suggestions["summary"],
                    provider,
                    model,
                ),
            )
            transaction.execute(
                "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'Ticket',?,?)",
                (user["MaUser"], "TICKET_AI_ASSIST", parsed_id, request.client.host if request.client else None),
            )
        return JSONResponse(
            {"id": analysis_id, **suggestions, "status": "Pending", "aiProvider": provider, "requiresHumanReview": True},
            status_code=201,
        )

    @app.post("/api/tickets/{ticket_id}/ai-assist/{analysis_id}/review")
    def review_ai_assist(ticket_id: str, analysis_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Agent")
        parsed_ticket_id = numeric_id(ticket_id)
        parsed_analysis_id = numeric_id(analysis_id)
        decision = payload.get("decision")
        if decision not in {"selected", "dismissed"}:
            raise ApiError(400, "INVALID_INPUT")
        review_status = "Selected" if decision == "selected" else "Dismissed"
        with database.transaction() as transaction:
            ticket = transaction.fetch_one("SELECT MaAgent,TrangThai FROM Ticket WHERE MaTicket=? FOR UPDATE", (parsed_ticket_id,))
            if not ticket or ticket["MaAgent"] != user["MaUser"]:
                raise ApiError(404, "TICKET_NOT_FOUND")
            if ticket["TrangThai"] != STAGES[1]:
                raise ApiError(409, "TICKET_READ_ONLY")
            analysis = transaction.fetch_one(
                "SELECT ReviewStatus FROM TicketAIAnalysis WHERE MaAnalysis=? AND MaTicket=? FOR UPDATE",
                (parsed_analysis_id, parsed_ticket_id),
            )
            if not analysis:
                raise ApiError(404, "AI_SUGGESTION_NOT_FOUND")
            if analysis["ReviewStatus"] != "Pending":
                if analysis["ReviewStatus"] == review_status:
                    return {"id": parsed_analysis_id, "status": review_status}
                raise ApiError(409, "AI_SUGGESTION_REVIEWED")
            transaction.execute(
                "UPDATE TicketAIAnalysis SET ReviewStatus=?,ReviewedBy=?,ReviewedAt=UTC_TIMESTAMP(3) WHERE MaAnalysis=?",
                (review_status, user["MaUser"], parsed_analysis_id),
            )
            transaction.execute(
                "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'Ticket',?,?)",
                (user["MaUser"], "TICKET_AI_" + review_status.upper(), parsed_ticket_id, request.client.host if request.client else None),
            )
        return {"id": parsed_analysis_id, "status": review_status}
