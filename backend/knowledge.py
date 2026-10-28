import hashlib
import json
import re
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.ai import AIProvider, cosine, split_knowledge, valid_vector
from backend.auth import _require_role, current_user
from backend.db import Database, Transaction
from backend.errors import ApiError


KB_FIELDS = "MaKB id,TieuDe title,NoiDung content,TrangThai status,ContentVersion version,ReplacesId replacesId,NgayTao createdAt"
KEY_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def numeric_id(value: str | int) -> int:
    raw = str(value)
    if not re.fullmatch(r"[1-9]\d{0,9}", raw) or int(raw) > 2147483647:
        raise ApiError(400, "INVALID_INPUT")
    return int(raw)


def required_text(value: object, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ApiError(400, "INVALID_INPUT")
    return value.strip()


def parse_vector(value: object) -> list[float] | None:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, list) else None


def is_indexed(rows: list[dict[str, Any]], content: str, ai: AIProvider) -> bool:
    texts = split_knowledge(content or "")
    if not rows or len(rows) != len(texts):
        return False
    for row, expected in zip(rows, texts, strict=True):
        vector = parse_vector(row.get("embedding"))
        if (
            row.get("content") != expected
            or row.get("model") != ai.model
            or row.get("dimensions") != ai.dimensions
            or not valid_vector(vector, ai.dimensions)
        ):
            return False
    return True


def _request_hash(path: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps([path, payload], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _audit(transaction: Transaction, request: Request, user_id: int, document_id: int, action: str) -> None:
    transaction.execute(
        "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'KnowledgeBase',?,?)",
        (user_id, action, document_id, request.client.host if request.client else None),
    )


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
        if not actor or not actor["TrangThai"] or actor["TenRole"] != "Admin":
            raise ApiError(403, "FORBIDDEN")
        old = transaction.fetch_one(
            "SELECT RequestHash,Result FROM KnowledgeRequest WHERE MaUser=? AND RequestKey=?",
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
            "INSERT INTO KnowledgeRequest(MaUser,RequestKey,RequestHash,Result) VALUES(?,?,?,?)",
            (user["MaUser"], key, request_hash, json.dumps(result, ensure_ascii=False, separators=(",", ":"))),
        )
        return result


def _document(transaction: Transaction, document_id: int, version: int) -> dict[str, Any]:
    document = transaction.fetch_one(f"SELECT {KB_FIELDS} FROM KnowledgeBase WHERE MaKB=? FOR UPDATE", (document_id,))
    if not document:
        raise ApiError(404, "KNOWLEDGE_NOT_FOUND")
    if document["version"] != version:
        raise ApiError(409, "KNOWLEDGE_CHANGED")
    return document


def _chunks(transaction: Transaction, document_id: int) -> list[dict[str, Any]]:
    return transaction.fetch_all(
        "SELECT MaChunk id,ThuTu position,NoiDung content,Embedding embedding,TenMoHinh model,SoChieu dimensions "
        "FROM KnowledgeChunk WHERE MaKB=? ORDER BY ThuTu",
        (document_id,),
    )


def install_knowledge_routes(app: FastAPI, database: Database, ai: AIProvider, threshold: float = 0.35) -> None:
    @app.get("/api/knowledge")
    def list_documents(request: Request, before: str | None = None) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        cursor = numeric_id(before) if before is not None else None
        rows = database.fetch_all(
            "SELECT MaKB id,TieuDe title,TrangThai status,ContentVersion version,ReplacesId replacesId FROM KnowledgeBase "
            f"{'WHERE MaKB<? ' if cursor else ''}ORDER BY MaKB DESC LIMIT 31",
            (cursor,) if cursor else (),
        )
        documents = rows[:30]
        return {
            "documents": documents,
            "next": documents[-1]["id"] if len(rows) > 30 else None,
            "aiConfigured": ai.enabled,
            "aiProvider": ai.provider,
        }

    @app.get("/api/knowledge/{document_id}")
    def document_detail(document_id: str, request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        parsed_id = numeric_id(document_id)
        document = database.fetch_one(f"SELECT {KB_FIELDS} FROM KnowledgeBase WHERE MaKB=?", (parsed_id,))
        if not document:
            raise ApiError(404, "KNOWLEDGE_NOT_FOUND")
        chunks = database.fetch_all(
            "SELECT MaChunk id,ThuTu position,NoiDung content,Embedding embedding,TenMoHinh model,SoChieu dimensions "
            "FROM KnowledgeChunk WHERE MaKB=? ORDER BY ThuTu",
            (parsed_id,),
        )
        return {
            "document": document,
            "chunks": [{key: value for key, value in row.items() if key != "embedding"} for row in chunks],
            "indexed": is_indexed(chunks, document["content"] or "", ai),
            "aiConfigured": ai.enabled,
            "aiProvider": ai.provider,
        }

    @app.post("/api/knowledge", status_code=201)
    def create_document(payload: dict[str, Any], request: Request) -> JSONResponse:
        user = current_user(request, database)
        _require_role(user, "Admin")
        title = required_text(payload.get("title"), 200)
        content = required_text(payload.get("content"), 16000)
        replaces_id = numeric_id(payload["replacesId"]) if payload.get("replacesId") else None
        body = {"title": title, "content": content, "replacesId": replaces_id}

        def work(transaction: Transaction) -> dict[str, Any]:
            if replaces_id:
                previous = transaction.fetch_one("SELECT TrangThai FROM KnowledgeBase WHERE MaKB=? FOR UPDATE", (replaces_id,))
                if not previous or previous["TrangThai"] != "Đã xuất bản":
                    raise ApiError(409, "KNOWLEDGE_CHANGED")
            new_id = transaction.execute(
                "INSERT INTO KnowledgeBase(MaUser,TieuDe,NoiDung,LoaiTaiLieu,ReplacesId) VALUES(?,?,?,'Text',?)",
                (user["MaUser"], title, content, replaces_id),
            )
            _audit(transaction, request, user["MaUser"], new_id, "KNOWLEDGE_CREATE")
            return {"id": new_id}

        result = _mutate(database, request, user, body, work)
        return JSONResponse(result, status_code=200 if result.get("replayed") else 201)

    @app.post("/api/knowledge/{document_id}/save")
    def save_document(document_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        parsed_id = numeric_id(document_id)
        version = numeric_id(payload.get("version"))
        title = required_text(payload.get("title"), 200)
        content = required_text(payload.get("content"), 16000)
        body = {"version": version, "title": title, "content": content}

        def work(transaction: Transaction) -> dict[str, Any]:
            document = _document(transaction, parsed_id, version)
            if document["status"] != "Nháp":
                raise ApiError(409, "KNOWLEDGE_READ_ONLY")
            transaction.execute("DELETE FROM KnowledgeChunk WHERE MaKB=?", (parsed_id,))
            transaction.execute(
                "UPDATE KnowledgeBase SET TieuDe=?,NoiDung=?,ContentVersion=ContentVersion+1,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaKB=?",
                (title, content, parsed_id),
            )
            _audit(transaction, request, user["MaUser"], parsed_id, "KNOWLEDGE_EDIT")
            return {"id": parsed_id}

        return _mutate(database, request, user, body, work)

    @app.post("/api/knowledge/{document_id}/index")
    def index_document(document_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        parsed_id = numeric_id(document_id)
        version = numeric_id(payload.get("version"))
        body = {"version": version}
        key = request.headers.get("idempotency-key", "")
        if not KEY_PATTERN.fullmatch(key):
            raise ApiError(400, "REQUEST_KEY_REQUIRED")
        request_hash = _request_hash(request.url.path, body)
        old = database.fetch_one(
            "SELECT RequestHash,Result FROM KnowledgeRequest WHERE MaUser=? AND RequestKey=?",
            (user["MaUser"], key),
        )
        if old:
            if old["RequestHash"] != request_hash:
                raise ApiError(409, "REQUEST_KEY_CONFLICT")
            result = old["Result"] if isinstance(old["Result"], dict) else json.loads(old["Result"])
            return {**result, "replayed": True}
        document = database.fetch_one(f"SELECT {KB_FIELDS} FROM KnowledgeBase WHERE MaKB=?", (parsed_id,))
        if not document:
            raise ApiError(404, "KNOWLEDGE_NOT_FOUND")
        if document["version"] != version:
            raise ApiError(409, "KNOWLEDGE_CHANGED")
        if document["status"] != "Nháp":
            raise ApiError(409, "KNOWLEDGE_READ_ONLY")
        chunks = split_knowledge(document["content"] or "")
        if not chunks:
            raise ApiError(400, "INVALID_INPUT")
        vectors = ai.embed(chunks)
        if len(vectors) != len(chunks) or any(not valid_vector(vector, ai.dimensions) for vector in vectors):
            raise ApiError(503, "AI_INVALID_OUTPUT")

        def work(transaction: Transaction) -> dict[str, Any]:
            current = _document(transaction, parsed_id, version)
            if current["status"] != "Nháp":
                raise ApiError(409, "KNOWLEDGE_READ_ONLY")
            transaction.execute("DELETE FROM KnowledgeChunk WHERE MaKB=?", (parsed_id,))
            for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                transaction.execute(
                    "INSERT INTO KnowledgeChunk(MaKB,ThuTu,NoiDung,Embedding,TenMoHinh,SoChieu) VALUES(?,?,?,?,?,?)",
                    (parsed_id, position, chunk, json.dumps(vector, separators=(",", ":")), ai.model, ai.dimensions),
                )
            _audit(transaction, request, user["MaUser"], parsed_id, "KNOWLEDGE_INDEX")
            return {"id": parsed_id}

        return _mutate(database, request, user, body, work)

    @app.post("/api/knowledge/{document_id}/preview")
    def preview_document(document_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        parsed_id = numeric_id(document_id)
        question = required_text(payload.get("question"), 3000)
        version = numeric_id(payload.get("version"))
        document = database.fetch_one(f"SELECT {KB_FIELDS} FROM KnowledgeBase WHERE MaKB=?", (parsed_id,))
        if not document:
            raise ApiError(404, "KNOWLEDGE_NOT_FOUND")
        if document["version"] != version:
            raise ApiError(409, "KNOWLEDGE_CHANGED")
        chunks = database.fetch_all(
            "SELECT MaChunk id,NoiDung content,Embedding embedding,TenMoHinh model,SoChieu dimensions "
            "FROM KnowledgeChunk WHERE MaKB=? ORDER BY ThuTu",
            (parsed_id,),
        )
        if not is_indexed(chunks, document["content"] or "", ai):
            raise ApiError(409, "KNOWLEDGE_NOT_INDEXED")
        query_vector = ai.embed([question], "query")[0]
        ranked = []
        for chunk in chunks:
            vector = parse_vector(chunk["embedding"])
            score = cosine(query_vector, vector) if vector is not None else -1
            if score >= getattr(ai, "retrieval_threshold", threshold):
                ranked.append({**chunk, "title": document["title"], "score": score})
        ranked = sorted(ranked, key=lambda row: (-row["score"], row["id"]))[:3]
        answer = ai.answer(question, ranked, "en" if payload.get("language") == "en" else "vi") if ranked else {"text": "", "sourceIds": []}
        sources = [
            {key: value for key, value in row.items() if key != "embedding"}
            for row in ranked
            if row["id"] in answer["sourceIds"]
        ]
        return {"answer": answer["text"], "sources": sources, "preview": True}

    for operation in ("publish", "archive"):
        @app.post(f"/api/knowledge/{{document_id}}/{operation}")
        def change_document_state(document_id: str, payload: dict[str, Any], request: Request, action: str = operation) -> dict[str, Any]:
            user = current_user(request, database)
            _require_role(user, "Admin")
            parsed_id = numeric_id(document_id)
            version = numeric_id(payload.get("version"))

            def work(transaction: Transaction) -> dict[str, Any]:
                document = _document(transaction, parsed_id, version)
                if action == "publish":
                    if document["status"] != "Nháp" or not is_indexed(_chunks(transaction, parsed_id), document["content"] or "", ai):
                        raise ApiError(409, "KNOWLEDGE_NOT_INDEXED" if document["status"] == "Nháp" else "KNOWLEDGE_READ_ONLY")
                    if document["replacesId"]:
                        old_document = transaction.fetch_one("SELECT TrangThai FROM KnowledgeBase WHERE MaKB=? FOR UPDATE", (document["replacesId"],))
                        if not old_document or old_document["TrangThai"] != "Đã xuất bản":
                            raise ApiError(409, "KNOWLEDGE_CHANGED")
                        transaction.execute(
                            "UPDATE KnowledgeBase SET TrangThai='Lưu trữ',NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaKB=?",
                            (document["replacesId"],),
                        )
                        _audit(transaction, request, user["MaUser"], document["replacesId"], "KNOWLEDGE_SUPERSEDED")
                elif document["status"] != "Đã xuất bản":
                    raise ApiError(409, "KNOWLEDGE_READ_ONLY")
                target = "Đã xuất bản" if action == "publish" else "Lưu trữ"
                transaction.execute(
                    "UPDATE KnowledgeBase SET TrangThai=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaKB=?",
                    (target, parsed_id),
                )
                _audit(transaction, request, user["MaUser"], parsed_id, "KNOWLEDGE_" + action.upper())
                return {"id": parsed_id}

            return _mutate(database, request, user, {"version": version}, work)
