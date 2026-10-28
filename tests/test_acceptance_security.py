"""Acceptance regressions for the explicitly supplied requirements."""

import pytest
from fastapi.testclient import TestClient
from backend.ai import mask_display, redact_sensitive, AIProvider
from backend.app import create_app
from backend.config import Settings


@pytest.mark.parametrize(
    "text,secret",
    [
        ("OTP: 938471", "938471"),
        ("OTP is 938471", "938471"),
        ("CMND của tôi là 123456789", "123456789"),
        ("my password is Strong-Secret-2026!", "Strong-Secret-2026!"),
        ("CVV 391", "391"),
        ("CVC=582", "582"),
        ("PIN 9432", "9432"),
        ("CCCD: 123456789012", "123456789012"),
        ("CMND 123456789", "123456789"),
        ("căn cước công dân: 123456789012", "123456789012"),
        ("mật khẩu: Pass@123456", "Pass@123456"),
        ("4532-xxxx-xxxx-1234", "4532-xxxx-xxxx-1234"),
        ("one-time code: 928471", "928471"),
    ],
)
def test_sensitive_codes_are_hidden_from_ai_and_display(text, secret):
    assert secret not in redact_sensitive(text)
    assert secret not in mask_display(text)


def test_masking_keeps_non_secret_support_details():
    text = "Ticket 123, CVV là mã bảo mật. Điểm 5 sao, thời gian 24 giờ."
    assert mask_display(text) == text


@pytest.mark.parametrize(
    "text", ["I need password reset help", "Mật khẩu của tôi không hoạt động"]
)
def test_password_support_questions_keep_their_meaning(text):
    assert redact_sensitive(text) == text


def test_invalid_content_length_is_rejected_without_server_error():
    client = TestClient(create_app(lambda: None))
    result = client.post(
        "/api/test",
        content="{}",
        headers={
            "Origin": "http://localhost:3000",
            "X-Vietincare-Request": "1",
            "Content-Type": "application/json",
            "Content-Length": "invalid",
        },
    )
    assert result.status_code == 400


def test_oversized_body_without_content_length_is_rejected():
    client = TestClient(create_app(lambda: None))
    result = client.post(
        "/api/test",
        content=iter([b" " * 70000]),
        headers={
            "Origin": "http://localhost:3000",
            "X-Vietincare-Request": "1",
            "Content-Type": "application/json",
        },
    )
    assert result.status_code == 413


def test_classifier_validates_label_and_masks_sensitive_input(monkeypatch):
    ai = AIProvider(Settings.from_env({"GEMINI_API_KEY": "test-only-placeholder"}))
    captured = {}

    def respond(instructions, payload, *args):
        captured.update(payload)
        return {
            "category": "Tài khoản",
            "priority": "Khẩn cấp",
            "sentiment": "Bức xúc cao",
        }

    monkeypatch.setattr(ai, "_structured_request", respond)
    assert (
        ai.classify_context("OTP 829471 và CVV 839", ["Tài khoản"])["sentiment"]
        == "Bức xúc cao"
    )
    assert "829471" not in captured["content"] and "839" not in captured["content"]


def test_category_labels_are_also_redacted_before_external_ai(monkeypatch):
    ai = AIProvider(Settings.from_env({"GEMINI_API_KEY": "test-only-placeholder"}))
    captured = {}

    def respond(instructions, payload, *args):
        captured.update(payload)
        return {
            "category": payload["categories"][0],
            "priority": "Cao",
            "sentiment": "Trung tính",
        }

    monkeypatch.setattr(ai, "_structured_request", respond)
    result = ai.classify_context("Cần hỗ trợ", ["OTP 829471"])
    assert "829471" not in captured["categories"][0]
    assert result["category"] == "OTP 829471"
