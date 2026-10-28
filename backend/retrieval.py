"""Shared published-only retrieval for Chat RAG and Agent draft context."""

from typing import Any
from backend.ai import AIProvider, rank_chunks
from backend.db import Database
from backend.errors import ApiError


def retrieve(database: Database, ai: AIProvider, question: str) -> list[dict[str, Any]]:
    rows = database.fetch_all(
        "SELECT k.MaChunk id,k.NoiDung content,k.Embedding embedding,b.MaKB documentId,b.TieuDe title,b.ContentVersion version "
        "FROM KnowledgeChunk k JOIN KnowledgeBase b ON b.MaKB=k.MaKB "
        "WHERE b.TrangThai='Đã xuất bản' AND k.TenMoHinh=? AND k.SoChieu=? ORDER BY k.MaChunk LIMIT 1001",
        (ai.model, ai.dimensions),
    )
    if len(rows) > 1000:
        raise ApiError(503, "KNOWLEDGE_LIMIT")
    if not rows:
        return []
    vector = ai.embed([question], "query")[0]
    selected = rank_chunks(rows, vector, getattr(ai, "retrieval_threshold", 0.35))
    return [
        {key: row[key] for key in ("id", "documentId", "title", "content", "version")}
        for row in selected
    ]
