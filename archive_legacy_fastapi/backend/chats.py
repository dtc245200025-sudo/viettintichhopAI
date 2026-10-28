import hashlib
import json
import re
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.ai import AIProvider, cosine
from backend.auth import _require_role, current_user
from backend.db import Database, Transaction
from backend.errors import ApiError


CHAT_FIELDS = "MaSession id,TieuDe title,TrangThai status,ThoiGianBatDau createdAt,ThoiGianKetThuc closedAt"
KEY_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _id(value: str | int) -> int:
    raw = str(value)
    if not re.fullmatch(r"[1-9]\d{0,9}", raw) or int(raw) > 2147483647:
        raise ApiError(400, "INVALID_INPUT")
    return int(raw)


def _content(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 3000:
        raise ApiError(400, "INVALID_INPUT")
    return value.strip()


def _request_hash(path: str, payload: dict[str, Any]) -> str:
    value = json.dumps([path, payload], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mutate(
    database: Database,
    request: Request,
    user: dict[str, Any],
    payload: dict[str, Any],
    work: Callable[[Transaction], dict[str, Any]],
) -> dict[str, Any]:
    key = request.headers.get("idempotency-key", "")
    if not KEY_PATTERN.fullmatch(key):
        raise ApiError(400, "REQUEST_KEY_REQUIRED")
    request_hash = _request_hash(request.url.path, payload)
    with database.transaction() as transaction:
        actor = transaction.fetch_one(
            "SELECT u.TrangThai,r.TenRole FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole WHERE u.MaUser=? FOR UPDATE",
            (user["MaUser"],),
        )
        if not actor or not actor["TrangThai"]:
            raise ApiError(401, "UNAUTHENTICATED")
        if actor["TenRole"] != "Customer":
            raise ApiError(403, "FORBIDDEN")
        owner = transaction.fetch_one(
            "SELECT MaKH FROM Customer WHERE MaKH=? AND MaUser=? AND TrangThai=1 FOR UPDATE",
            (user["MaKH"], user["MaUser"]),
        )
        if not owner:
            raise ApiError(403, "FORBIDDEN")
        old = transaction.fetch_one(
            "SELECT RequestHash,Result FROM ChatRequest WHERE MaUser=? AND RequestKey=?",
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
            "INSERT INTO ChatRequest(MaUser,RequestKey,RequestHash,Result) VALUES(?,?,?,?)",
            (user["MaUser"], key, request_hash, json.dumps(result, ensure_ascii=False, separators=(",", ":"))),
        )
        return result


def _record(transaction: Transaction, request: Request, user_id: int, chat_id: int, action: str) -> None:
    transaction.execute(
        "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'ChatSession',?,?)",
        (user_id, action, chat_id, request.client.host if request.client else None),
    )


def _owned(transaction: Transaction, user: dict[str, Any], chat_id: int) -> dict[str, Any]:
    chat = transaction.fetch_one(
        f"SELECT {CHAT_FIELDS} FROM ChatSession WHERE MaSession=? AND MaKH=? FOR UPDATE",
        (chat_id, user["MaKH"]),
    )
    if not chat:
        raise ApiError(404, "CHAT_NOT_FOUND")
    return chat


def install_chat_routes(app: FastAPI, database: Database, ai: AIProvider, threshold: float = 0.35) -> None:
    @app.get("/api/chats")
    def list_chats(request: Request, before: str | None = None) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        cursor = _id(before) if before is not None else None
        rows = database.fetch_all(
            f"SELECT {CHAT_FIELDS} FROM ChatSession WHERE MaKH=? {'AND MaSession<? ' if cursor else ''}"
            "ORDER BY MaSession DESC LIMIT 31",
            (user["MaKH"], *((cursor,) if cursor else ())),
        )
        chats = rows[:30]
        return {
            "chats": chats,
            "next": chats[-1]["id"] if len(rows) > 30 else None,
            "aiProvider": ai.provider,
            "assistantStatus": "ready" if ai.enabled else "not_configured",
        }

    @app.get("/api/chats/{chat_id}")
    def chat_detail(request: Request, chat_id: str, before: str | None = None) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        parsed_id = _id(chat_id)
        cursor = _id(before) if before is not None else None
        chat = database.fetch_one(
            f"SELECT {CHAT_FIELDS} FROM ChatSession WHERE MaSession=? AND MaKH=?",
            (parsed_id, user["MaKH"]),
        )
        if not chat:
            raise ApiError(404, "CHAT_NOT_FOUND")
        rows = database.fetch_all(
            "SELECT MaMessage id,NguoiGui sender,MaUser userId,NoiDung content,ThoiGian createdAt,ReplyTo replyTo,AnswerStatus answerStatus "
            f"FROM Message WHERE MaSession=? {'AND MaMessage<? ' if cursor else ''}ORDER BY MaMessage DESC LIMIT 51",
            (parsed_id, *((cursor,) if cursor else ())),
        )
        messages = rows[:50]
        if messages:
            ids = [message["id"] for message in messages]
            placeholders = ",".join("?" for _ in ids)
            sources = database.fetch_all(
                "SELECT s.MaMessage messageId,s.MaChunk chunkId,k.MaKB documentId,s.TieuDeNguon title,s.NoiDungNguon content "
                f"FROM MessageSource s JOIN KnowledgeChunk k ON k.MaChunk=s.MaChunk WHERE s.MaMessage IN ({placeholders}) ORDER BY s.MaSource",
                tuple(ids),
            )
            for message in messages:
                message["sources"] = [source for source in sources if source["messageId"] == message["id"]]
        messages.reverse()
        return {
            "chat": chat,
            "messages": messages,
            "next": rows[49]["id"] if len(rows) > 50 else None,
            "aiProvider": ai.provider,
            "assistantStatus": "ready" if ai.enabled else "not_configured",
        }

    @app.post("/api/chats", status_code=201)
    def create_chat(payload: dict[str, Any], request: Request) -> JSONResponse:
        user = current_user(request, database)
        _require_role(user, "Customer")
        content = _content(payload.get("content"))

        def work(transaction: Transaction) -> dict[str, Any]:
            chat_id = transaction.execute(
                "INSERT INTO ChatSession(MaKH,TieuDe,KenhChat) VALUES(?,?,'Web')",
                (user["MaKH"], "".join(list(content)[:100])),
            )
            message_id = transaction.execute(
                "INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",
                (chat_id, user["MaUser"], content),
            )
            _record(transaction, request, user["MaUser"], chat_id, "CHAT_CREATE")
            return {"id": chat_id, "messageId": message_id, "assistantStatus": "ready" if ai.enabled else "not_configured"}

        result = _mutate(database, request, user, {"content": content}, work)
        return JSONResponse(result, status_code=200 if result.get("replayed") else 201)

    @app.post("/api/chats/{chat_id}/messages")
    def create_message(chat_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        parsed_id = _id(chat_id)
        content = _content(payload.get("content"))

        def work(transaction: Transaction) -> dict[str, Any]:
            chat = _owned(transaction, user, parsed_id)
            if chat["closedAt"] or chat["status"] != "Đang hoạt động":
                raise ApiError(409, "CHAT_READ_ONLY")
            message_id = transaction.execute(
                "INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",
                (parsed_id, user["MaUser"], content),
            )
            _record(transaction, request, user["MaUser"], parsed_id, "CHAT_MESSAGE")
            return {"id": parsed_id, "messageId": message_id, "assistantStatus": "ready" if ai.enabled else "not_configured"}

        return _mutate(database, request, user, {"content": content}, work)

    @app.post("/api/chats/{chat_id}/close")
    def close_chat(chat_id: str, request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        parsed_id = _id(chat_id)

        def work(transaction: Transaction) -> dict[str, Any]:
            chat = _owned(transaction, user, parsed_id)
            if not chat["closedAt"]:
                if chat["status"] != "Đang hoạt động":
                    raise ApiError(409, "CHAT_READ_ONLY")
                transaction.execute(
                    "UPDATE ChatSession SET TrangThai='Đã kết thúc',ThoiGianKetThuc=UTC_TIMESTAMP(3) WHERE MaSession=?",
                    (parsed_id,),
                )
                transaction.execute(
                    "UPDATE Handover SET TrangThai='Đã hủy',ThoiGianKetThuc=UTC_TIMESTAMP(3) "
                    "WHERE MaSession=? AND TrangThai IN ('Chờ tiếp nhận','Đã tiếp nhận')",
                    (parsed_id,),
                )
                _record(transaction, request, user["MaUser"], parsed_id, "CHAT_CLOSE")
            return {"id": parsed_id}

        return _mutate(database, request, user, {}, work)

    @app.post("/api/chats/{chat_id}/messages/{message_id}/answer")
    def answer_message(chat_id: str, message_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Customer")
        parsed_chat_id, parsed_message_id = _id(chat_id), _id(message_id)
        language = "en" if payload.get("language") == "en" else "vi"
        source = database.fetch_one(
            "SELECT m.NoiDung content FROM Message m JOIN ChatSession s ON s.MaSession=m.MaSession "
            "WHERE m.MaMessage=? AND m.MaSession=? AND m.MaUser=? AND m.NguoiGui='Customer' AND s.MaKH=?",
            (parsed_message_id, parsed_chat_id, user["MaUser"], user["MaKH"]),
        )
        if not source:
            raise ApiError(404, "CHAT_NOT_FOUND")
        if not ai.enabled:
            raise ApiError(503, "AI_NOT_CONFIGURED")
        connection = database.pool.get_connection()
        lock_name = f"vc:rag:{hashlib.sha256(str(database.pool.pool_name).encode()).hexdigest()[:16]}:{parsed_message_id}"
        acquired = False
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute("SELECT GET_LOCK(%s,0) ok", (lock_name,))
                acquired = bool(cursor.fetchone()["ok"])
            finally:
                cursor.close()
            if not acquired:
                raise ApiError(409, "AI_BUSY")
            old = database.fetch_one("SELECT MaMessage id,AnswerStatus status FROM Message WHERE ReplyTo=?", (parsed_message_id,))
            if old:
                return {"messageId": old["id"], "status": old["status"], "replayed": True}
            chat = database.fetch_one("SELECT TrangThai,ThoiGianKetThuc FROM ChatSession WHERE MaSession=?", (parsed_chat_id,))
            if not chat or chat["TrangThai"] != "Đang hoạt động" or chat["ThoiGianKetThuc"]:
                raise ApiError(409, "CHAT_READ_ONLY")
            if database.fetch_one(
                "SELECT MaHandover FROM Handover WHERE MaSession=? AND TrangThai IN ('Chờ tiếp nhận','Đã tiếp nhận') LIMIT 1",
                (parsed_chat_id,),
            ):
                raise ApiError(409, "HANDOVER_ACTIVE")
            chunks = database.fetch_all(
                "SELECT k.MaChunk id,k.NoiDung content,k.Embedding embedding,k.TenMoHinh model,k.SoChieu dimensions,"
                "b.MaKB documentId,b.TieuDe title,b.ContentVersion version FROM KnowledgeChunk k "
                "JOIN KnowledgeBase b ON b.MaKB=k.MaKB WHERE b.TrangThai='Đã xuất bản' AND k.TenMoHinh=? AND k.SoChieu=? "
                "ORDER BY k.MaChunk LIMIT 1001",
                (ai.model, ai.dimensions),
            )
            if len(chunks) > 1000:
                raise ApiError(503, "KNOWLEDGE_LIMIT")
            selected: list[dict[str, Any]] = []
            answer = {"text": "", "sourceIds": []}
            if chunks:
                vector = ai.embed([source["content"]], "query")[0]
                for row in chunks:
                    try:
                        candidate = json.loads(row["embedding"]) if isinstance(row["embedding"], str) else row["embedding"]
                    except (TypeError, json.JSONDecodeError):
                        continue
                    row["score"] = cosine(vector, candidate) if isinstance(candidate, list) else -1
                effective_threshold = getattr(ai, "retrieval_threshold", threshold)
                selected = sorted((row for row in chunks if row.get("score", -1) >= effective_threshold), key=lambda row: (-row["score"], row["id"]))[:3]
                if selected:
                    answer = ai.answer(source["content"], selected, language)
            if not isinstance(answer.get("text"), str) or any(
                not isinstance(source_id, int) or not any(row["id"] == source_id for row in selected)
                for source_id in answer.get("sourceIds", [])
            ):
                raise ApiError(503, "AI_INVALID_OUTPUT")
            used = [row for row in selected if row["id"] in answer["sourceIds"]] if answer["text"] else []
            if not used:
                output_text = (
                    "I could not find enough published information to answer this question. Please create a support ticket for help."
                    if language == "en"
                    else "Chưa tìm thấy đủ thông tin đã xuất bản để trả lời câu hỏi này. Bạn có thể tạo yêu cầu để được nhân viên hỗ trợ."
                )
                status = "no_sources"
            else:
                output_text, status = answer["text"], "answered"
            with database.transaction() as transaction:
                owner = transaction.fetch_one(
                    "SELECT u.TrangThai,r.TenRole,c.MaKH FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole "
                    "JOIN Customer c ON c.MaUser=u.MaUser AND c.TrangThai=1 WHERE u.MaUser=? FOR UPDATE",
                    (user["MaUser"],),
                )
                if not owner or not owner["TrangThai"] or owner["TenRole"] != "Customer" or owner["MaKH"] != user["MaKH"]:
                    raise ApiError(403, "FORBIDDEN")
                current_chat = transaction.fetch_one(
                    "SELECT TrangThai,ThoiGianKetThuc FROM ChatSession WHERE MaSession=? AND MaKH=? FOR UPDATE",
                    (parsed_chat_id, owner["MaKH"]),
                )
                if not current_chat or current_chat["TrangThai"] != "Đang hoạt động" or current_chat["ThoiGianKetThuc"]:
                    raise ApiError(409, "CHAT_READ_ONLY")
                for row in sorted(used, key=lambda item: item["documentId"]):
                    document = transaction.fetch_one("SELECT TrangThai,ContentVersion FROM KnowledgeBase WHERE MaKB=? FOR SHARE", (row["documentId"],))
                    if not document or document["TrangThai"] != "Đã xuất bản" or document["ContentVersion"] != row["version"]:
                        raise ApiError(409, "KNOWLEDGE_CHANGED")
                reply_id = transaction.execute(
                    "INSERT INTO Message(MaSession,NguoiGui,NoiDung,ReplyTo,AnswerStatus) VALUES(?,'AI',?,?,?)",
                    (parsed_chat_id, output_text, parsed_message_id, status),
                )
                for row in used:
                    source_hash = hashlib.sha256(row["content"].encode("utf-8")).hexdigest()
                    transaction.execute(
                        "INSERT INTO MessageSource(MaMessage,MaChunk,TieuDeNguon,NoiDungNguon,SourceHash) VALUES(?,?,?,?,?)",
                        (reply_id, row["id"], row["title"], row["content"], source_hash),
                    )
                transaction.execute(
                    "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong) VALUES(?,'RAG_ANSWER','Message',?)",
                    (user["MaUser"], reply_id),
                )
            return {"messageId": reply_id, "status": status}
        finally:
            try:
                if acquired:
                    lock_cursor = connection.cursor()
                    try:
                        lock_cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                        lock_cursor.fetchone()
                    finally:
                        lock_cursor.close()
            finally:
                connection.close()
