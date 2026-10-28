import pytest
from pathlib import Path

from backend.ai import AIProvider
from backend.app import create_app
from backend.config import Settings
from backend.errors import ApiError
from backend.system_admin import _apply, _validated


def test_system_setting_validation_accepts_only_allowlisted_ranges() -> None:
    assert _validated("rag.threshold", 0.42) == ("rag.threshold", "0.42", "decimal")
    assert _validated("ai.timeout_seconds", 45) == ("ai.timeout_seconds", "45", "integer")
    for key, value in (("unknown", 1), ("rag.threshold", 1.1), ("ai.timeout_seconds", 4), ("ai.timeout_seconds", True)):
        with pytest.raises(ApiError, match="INVALID_INPUT"):
            _validated(key, value)


def test_system_setting_is_applied_to_running_ai_provider() -> None:
    provider = AIProvider(Settings.from_env({"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test", "APP_ORIGIN": "http://localhost:3000"}))

    _apply(provider, "rag.threshold", "0.55")
    _apply(provider, "ai.timeout_seconds", "50")

    assert provider.retrieval_threshold == 0.55
    assert provider.timeout_seconds == 50


def test_handover_settings_and_audit_routes_are_registered() -> None:
    class DatabaseWithoutMigratedSettings:
        def fetch_all(self, statement, parameters=()):
            raise RuntimeError("migration not applied")

    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    app = create_app(database=DatabaseWithoutMigratedSettings(), settings=settings)
    paths = {route.path for route in app.routes}

    assert "/api/chats/{chat_id}/handover" in paths
    assert "/api/handovers/{handover_id}/accept" in paths
    assert "/api/handovers/{handover_id}/summary" in paths
    assert "/api/admin/settings/{setting_key}" in paths
    assert "/api/admin/audit-logs" in paths


def test_vi_en_frontends_expose_handover_and_admin_controls() -> None:
    root = Path(__file__).resolve().parent.parent
    chat = (root / "chat.js").read_text(encoding="utf-8")
    account = (root / "account.js").read_text(encoding="utf-8")

    assert "/handover`" in chat
    assert "Yêu cầu nhân viên" in (root / "VI" / "chat-vi.html").read_text(encoding="utf-8")
    assert "Request an agent" in (root / "EN" / "chat-en.html").read_text(encoding="utf-8")
    assert "/api/admin/audit-logs" in account
    assert "/api/admin/settings/" in account
