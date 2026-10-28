"""Explicit deterministic simulation for testing only, never a fallback AI provider."""

from typing import Any
from backend.demo_data import DEMO_MODEL, DEMO_DIMENSIONS


class SimulationAI:
    enabled = True
    provider = "simulation"
    model = DEMO_MODEL
    dimensions = DEMO_DIMENSIONS
    retrieval_threshold = 0.35
    timeout_seconds = 30

    def embed(self, texts: list[str], purpose: str = "document") -> list[list[float]]:
        return [[1.0] + [0.0] * (self.dimensions - 1) for _ in texts]

    def classify_context(self, content: str, categories: list[str]) -> dict[str, str]:
        sentiment = (
            "Bức xúc cao"
            if any(
                s in content.lower()
                for s in ["bức xúc", "tức giận", "rất giận", "furious"]
            )
            else "Trung tính"
        )
        category = next(
            (c for c in categories if c.lower() in content.lower()),
            categories[0] if categories else "Cần kiểm tra",
        )
        return {
            "category": category,
            "priority": "Khẩn cấp" if sentiment == "Bức xúc cao" else "Trung bình",
            "sentiment": sentiment,
        }

    def answer(
        self, question: str, sources: list[dict[str, Any]], language: str
    ) -> dict[str, Any]:
        if not sources or any(
            s in question.lower()
            for s in ["ngoài nguồn", "lãi suất hôm nay", "outside sources"]
        ):
            return {"text": "", "sourceIds": []}
        return {
            "text": "[SIMULATION] " + sources[0]["content"],
            "sourceIds": [sources[0]["id"]],
        }

    def support_assist(
        self, context: dict[str, Any], language: str = "vi"
    ) -> dict[str, str]:
        return {
            "category": "Tài khoản",
            "priority": "Trung bình",
            "sentiment": "Trung tính",
            "draftReply": "[SIMULATION] Nhân viên cần kiểm tra và duyệt nội dung trước khi gửi.",
            "summary": "[SIMULATION] Khách cần hướng dẫn; đang chờ nhân viên xác nhận.",
        }

    def summarize_conversation(
        self, messages: list[dict[str, Any]], language: str = "vi"
    ) -> str:
        return (
            "[SIMULATION] Khách đã trao đổi "
            + str(len(messages))
            + " tin nhắn; cần nhân viên tiếp tục hỗ trợ."
        )
