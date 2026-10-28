from pathlib import Path

import pytest

from backend.config import Settings
from backend.security import digest, hash_password, verify_password
from backend.setup_db_user import APP_HOSTS
from backend.list_accounts import ACCOUNT_QUERY


def test_password_hash_uses_the_existing_mysql_format() -> None:
    stored = hash_password("SafePassword42!")

    assert stored.startswith("scrypt$32768$8$1$")
    assert verify_password("SafePassword42!", stored)
    assert not verify_password("DifferentPassword42!", stored)
    assert not verify_password("SafePassword42!", "legacy-password")


def test_digest_matches_sha256_for_session_and_request_keys() -> None:
    assert digest("vietincare").hex() == "8f6016ea162399a8872812913b3e9b89c9918abc45dc0bd3c7125ef7f66ce54d"


def test_local_mysql_app_account_covers_resolved_and_numeric_hosts() -> None:
    assert APP_HOSTS == ("localhost", "127.0.0.1")


def test_mysql_setup_buffers_identity_verification_result() -> None:
    source = (Path(__file__).resolve().parents[1] / "backend" / "setup_db_user.py").read_text(encoding="utf-8")
    assert "cursor(dictionary=True, buffered=True)" in source
    assert 'identity_cursor.fetchall()' in source


def test_account_inventory_query_never_reads_credentials_or_tokens() -> None:
    assert "PasswordHash" not in ACCOUNT_QUERY
    assert "Token" not in ACCOUNT_QUERY
    assert "UserAccount" in ACCOUNT_QUERY and "Role" in ACCOUNT_QUERY


def test_local_provisioning_supports_supervisor_role() -> None:
    source = (Path(__file__).resolve().parents[1] / "backend" / "provision.py").read_text(encoding="utf-8")
    launcher = (Path(__file__).resolve().parents[1] / "scripts" / "manage-local.ps1").read_text(encoding="utf-8")
    assert '"Supervisor": "VC_SUPERVISOR"' in source
    assert "'create-supervisor'" in launcher
    assert "--role Supervisor" in launcher


def test_settings_select_gemini_without_leaking_other_provider_key() -> None:
    settings = Settings.from_env({
        "GEMINI_API_KEY": "gemini-test-key",
        "OPENAI_API_KEY": "openai-test-key",
        "APP_ORIGIN": "http://localhost:3000",
    })

    assert settings.ai_provider == "gemini"
    assert settings.ai_key == "gemini-test-key"
    assert settings.ai_chat_model == "gemini-3.8-flash"
    assert settings.origin == "http://localhost:3000"


@pytest.mark.parametrize("overrides", [
    {"APP_ORIGIN": "http://localhost:3000/unsafe"},
    {"DB_NAME": "db-name"},
    {"PORT": "70000"},
    {"APP_ENV": "production", "APP_ORIGIN": "http://localhost:3000"},
])
def test_settings_reject_unsafe_or_invalid_values(overrides: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        Settings.from_env(overrides)
