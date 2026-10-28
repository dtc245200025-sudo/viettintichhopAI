import json

import httpx
import pytest

from backend.ai import AIProvider, cosine, redact_sensitive, split_knowledge, valid_vector
from backend.config import Settings
from backend.errors import ApiError


def settings(provider: str, key: str = "test-secret") -> Settings:
    key_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
    return Settings.from_env({"AI_PROVIDER": provider, key_name: key, "APP_ORIGIN": "http://localhost:3000"})


def test_vector_validation_and_cosine_reject_invalid_values() -> None:
    assert valid_vector([3.0, 4.0], 2)
    assert not valid_vector([0.0, 0.0], 2)
    assert not valid_vector([True, 1.0], 2)
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0], [1.0, 0.0]) == -1.0


def test_knowledge_chunks_overlap_without_splitting_unicode_characters() -> None:
    content = "á" * 1700
    chunks = split_knowledge(content)

    assert [len(chunk) for chunk in chunks] == [800, 800, 300]
    assert all(set(chunk) == {"á"} for chunk in chunks)


def test_personal_data_is_redacted_before_provider_requests() -> None:
    redacted = redact_sensitive(
        "Email user@example.test, phone +84 901234567, account 123456789012, "
        "password: Pass@123456, card 4532-xxxx-xxxx-1234, card 4532 1234 5678 1234"
    )

    assert "user@example.test" not in redacted
    assert "+84 901234567" not in redacted
    assert "123456789012" not in redacted
    assert "Pass@123456" not in redacted
    assert "4532-xxxx-xxxx-1234" not in redacted
    assert "4532 1234 5678 1234" not in redacted
    assert "[MASKED_PASSWORD]" in redacted
    assert redacted.count("[MASKED_CREDIT_CARD]") == 2


@pytest.mark.parametrize("value", [
    "mật khẩu cũ Pass@123456",
    "mat khau = Secret-2026!",
    "PWD: hidden-value",
    "passcode 123456",
])
def test_password_labels_are_masked_in_vietnamese_and_english(value: str) -> None:
    assert redact_sensitive(value) == "[MASKED_PASSWORD]"


def test_openai_embedding_request_uses_fixed_host_and_validates_vectors() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openai.com"
        assert request.headers["authorization"] == "Bearer test-secret"
        payload = json.loads(request.content)
        assert payload["dimensions"] == 512
        assert all("user@example.test" not in text for text in payload["input"])
        return httpx.Response(200, json={"data": [
            {"index": 1, "embedding": [0.0] * 511 + [1.0]},
            {"index": 0, "embedding": [1.0] + [0.0] * 511},
        ]})

    provider = AIProvider(settings("openai"), httpx.MockTransport(respond))
    vectors = provider.embed(["first user@example.test", "second"])

    assert vectors[0][0] == 1.0
    assert vectors[1][-1] == 1.0


def test_gemini_embedding_uses_query_task_and_normalizes_vector() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "test-secret"
        payload = json.loads(request.content)
        assert payload["requests"][0]["taskType"] == "RETRIEVAL_QUERY"
        return httpx.Response(200, json={"embeddings": [{"values": [3.0] + [0.0] * 767}]})

    vector = AIProvider(settings("gemini"), httpx.MockTransport(respond)).embed(["question"], "query")[0]

    assert vector[0] == 1.0
    assert valid_vector(vector, 768)


def test_gemini_3_answer_uses_low_thinking_and_structured_output() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models/gemini-3.8-flash:generateContent")
        payload = json.loads(request.content)
        generation = payload["generationConfig"]
        assert generation["thinkingConfig"] == {"thinkingLevel": "low"}
        assert generation["responseMimeType"] == "application/json"
        assert generation["responseJsonSchema"]["required"] == ["answer", "source_ids"]
        return httpx.Response(200, json={
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": json.dumps({"answer": "Có nguồn.", "source_ids": [7]})}]},
            }],
        })

    provider = AIProvider(settings("gemini"), httpx.MockTransport(respond))
    result = provider.answer("Câu hỏi", [{"id": 7, "title": "FAQ", "content": "Nội dung"}], "vi")

    assert result == {"text": "Có nguồn.", "sourceIds": [7]}


def test_ticket_assistance_redacts_personal_data_and_returns_human_review_draft() -> None:
    expected = {"category": "Login", "priority": "Cao", "sentiment": "Tiêu cực", "draft_reply": "Xin chào", "summary": "Không đăng nhập được"}

    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        sent_context = json.loads(payload["input"])
        assert "customer@example.test" not in sent_context["ticket_context"]
        assert "[MASKED_EMAIL]" in sent_context["ticket_context"]
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(expected, ensure_ascii=False)}]}]})

    provider = AIProvider(settings("openai"), httpx.MockTransport(respond))
    result = provider.support_assist({"content": "customer@example.test cannot sign in"})

    assert result["priority"] == "Cao"
    assert result["sentiment"] == "Tiêu cực"
    assert result["draftReply"] == "Xin chào"


def test_ai_provider_errors_do_not_expose_remote_response_body() -> None:
    provider = AIProvider(settings("openai"), httpx.MockTransport(lambda request: httpx.Response(429, text="private provider detail")))

    with pytest.raises(ApiError, match="AI_RATE_LIMITED"):
        provider.embed(["text"])


def test_conversation_summary_is_structured_and_redacts_personal_data() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        submitted = json.loads(payload["input"])
        assert "customer@example.test" not in json.dumps(submitted)
        assert payload["text"]["format"]["name"] == "conversation_summary"
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"summary": "Khách không đăng nhập được; cần kiểm tra email."}, ensure_ascii=False)}]}]})

    provider = AIProvider(settings("openai"), httpx.MockTransport(respond))
    summary = provider.summarize_conversation([{"sender": "Customer", "content": "customer@example.test không đăng nhập được"}])

    assert summary.startswith("Khách không đăng nhập")
