from fastapi.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock

from backend.app import create_app
from backend.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_health_requires_a_successful_database_probe() -> None:
    client = TestClient(create_app(lambda: None))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_hides_database_errors() -> None:
    def fail_probe() -> None:
        raise RuntimeError("private database details")

    response = TestClient(create_app(fail_probe)).get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"error": "SERVICE_UNAVAILABLE"}


def test_mutating_api_requires_expected_origin_and_json_marker() -> None:
    client = TestClient(create_app(lambda: None))

    response = client.post("/api/test", json={})

    assert response.status_code == 403
    assert response.json() == {"error": "ORIGIN_REJECTED"}


def test_api_responses_are_not_cached() -> None:
    response = TestClient(create_app(lambda: None)).get("/api/health")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_auth_routes_reject_missing_session_before_database_access() -> None:
    database = Mock()
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings))

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"error": "UNAUTHENTICATED"}
    database.fetch_one.assert_not_called()


def test_workspace_reports_role_specific_capabilities() -> None:
    database = Mock()
    database.fetch_one.return_value = {
        "MaUser": 7,
        "HoTen": "Supervisor Test",
        "Email": "supervisor@example.test",
        "TenRole": "Supervisor",
        "MaKH": None,
    }
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings))
    client.cookies.set("vietincare_session", "a" * 64)

    response = client.get("/api/workspace/Supervisor")

    assert response.status_code == 200
    assert "reports" in response.json()["implemented"]
    assert "reports" not in response.json()["pending"]
    assert response.json()["pending"] == []


def test_ticket_list_accepts_all_required_filters() -> None:
    database = Mock()
    database.fetch_one.return_value = {
        "MaUser": 7,
        "HoTen": "Supervisor Test",
        "Email": "supervisor@example.test",
        "TenRole": "Supervisor",
        "MaKH": None,
    }
    database.fetch_all.return_value = []
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings))
    client.cookies.set("vietincare_session", "a" * 64)

    response = client.get(
        "/api/tickets?customer=Lan&status=Ch%E1%BB%9D+kh%C3%A1ch+h%C3%A0ng&priority=Cao&startDate=2026-10-01&endDate=2026-10-27"
    )

    assert response.status_code == 200
    statement, parameters = database.fetch_all.call_args.args
    assert "c.HoTen LIKE" in statement
    assert "t.TrangThai=?" in statement
    assert "t.MucDoUuTien=?" in statement
    assert "t.NgayTao>=?" in statement
    assert "DATE_ADD(?,INTERVAL 1 DAY)" in statement
    assert parameters[-7:] == ("Chờ khách hàng", "Cao", "%Lan%", "%Lan%", "%Lan%", "2026-10-01", "2026-10-27")


def test_api_routes_are_registered_before_static_fallback() -> None:
    database = Mock()
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings, serve_static=True))

    api_response = client.get("/api/auth/me")
    report_response = client.get("/api/reports/summary")
    page_response = client.get("/VI/tickets-vi.html")
    profile_vi_response = client.get("/VI/account-profile-vi.html")
    profile_en_response = client.get("/EN/account-profile-en.html")
    report_style_response = client.get("/report.css")
    admin_style_response = client.get("/admin.css")
    private_file_response = client.get("/SQLQuery1.sql")

    assert api_response.status_code == 401
    assert report_response.status_code == 401
    assert page_response.status_code == 200
    assert "Yêu cầu hỗ trợ" in page_response.text
    assert profile_vi_response.status_code == 200
    assert profile_en_response.status_code == 200
    assert '<script src="../workspace.js"></script>' in profile_vi_response.text
    assert "account.js" not in profile_vi_response.text
    assert report_style_response.status_code == 200
    assert admin_style_response.status_code == 200
    assert private_file_response.status_code == 404


def test_landing_chat_uses_authenticated_chat_api_instead_of_canned_answers() -> None:
    script = (PROJECT_ROOT / "script.js").read_text(encoding="utf-8")

    assert 'chatGet("/api/auth/me")' in script
    assert 'chatPost("/api/chats", { content: text })' in script
    assert '/messages/${message.messageId}/answer' in script
    assert "getAIResponse" not in script
    assert "GEMINI_API_KEY" not in script


def test_knowledge_preview_clears_stale_answer_before_request() -> None:
    script = (PROJECT_ROOT / "knowledge.js").read_text(encoding="utf-8")

    submit = script.index("$('previewForm').addEventListener('submit'")
    clear = script.index("$('previewAnswer').textContent=''", submit)
    request = script.index("/preview`", submit)

    assert clear < request
