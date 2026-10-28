"""Real MySQL acceptance suite with explicit simulated AI and synthetic data."""

import json
import os
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import mysql.connector
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.db import Database
from backend.demo_ai import SimulationAI
from backend.demo_data import seed
from backend.migrations import migrate
from backend.automation import automate_ticket

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MYSQL_TESTS") != "1", reason="requires isolated MySQL 8.0.46"
)
PASSWORD = "Synthetic-Test-Only-2026!"


def post(client, path, payload=None, key=None):
    return client.post(
        path,
        json=payload or {},
        headers={
            "Origin": "http://localhost:3000",
            "X-Vietincare-Request": "1",
            "Idempotency-Key": key or str(uuid.uuid4()),
        },
    )


@pytest.fixture(scope="module")
def system():
    base = Settings.from_env()
    name = "vietincare_py_test_" + secrets.token_hex(6)
    settings = replace(base, database={**base.database, "database": name})
    migrate(settings, initialize=True)
    db = Database(settings.database)
    ai = SimulationAI()
    counts = seed(db, PASSWORD)
    assert counts["chunks"] == 1000
    assert seed(db, PASSWORD)["status"] == "already_seeded"
    # Runtime must work with CRUD only, while the test setup keeps its admin handle.
    options = {k: v for k, v in settings.database.items() if k != "database"}
    runtime_user = "vc_py_" + secrets.token_hex(6)
    runtime_password = secrets.token_urlsafe(24)
    with mysql.connector.connect(**options) as connection:
        cursor = connection.cursor()
        for host in ["localhost", "127.0.0.1"]:
            cursor.execute(
                f"CREATE USER '{runtime_user}'@'{host}' IDENTIFIED BY %s",
                (runtime_password,),
            )
            cursor.execute(
                f"GRANT SELECT,INSERT,UPDATE,DELETE ON `{name}`.* TO '{runtime_user}'@'{host}'"
            )
        cursor.close()
    db.pool._remove_connections()
    db = Database(
        {**settings.database, "user": runtime_user, "password": runtime_password}
    )
    app = create_app(database=db, settings=settings, ai=ai, serve_static=True)
    s = SimpleNamespace(db=db, ai=ai, app=app, settings=settings, clients={})
    for label in ["customer1", "customer2", "agent1", "agent2", "supervisor", "admin"]:
        client = TestClient(app, base_url=settings.origin)
        response = post(
            client,
            "/api/auth/login",
            {"email": label + "@demo.invalid", "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        s.clients[label] = client
    yield s
    for client in s.clients.values():
        client.close()
    db.pool._remove_connections()
    with mysql.connector.connect(**options) as connection:
        cursor = connection.cursor()
        cursor.execute(f"DROP DATABASE `{name}`")
        for host in ["localhost", "127.0.0.1"]:
            cursor.execute(f"DROP USER '{runtime_user}'@'{host}'")
        cursor.close()


def test_uc001_lockout_counts_failed_attempts_not_successful_logins(system):
    client = TestClient(
        system.app, base_url=system.settings.origin, client=("127.0.0.42", 40000)
    )
    for _ in range(6):
        assert (
            post(
                client,
                "/api/auth/login",
                {"email": "customer2@demo.invalid", "password": PASSWORD},
            ).status_code
            == 200
        )
    for _ in range(5):
        assert (
            post(
                client,
                "/api/auth/login",
                {"email": "customer2@demo.invalid", "password": "Wrong-Test-Password"},
            ).status_code
            == 401
        )
    assert (
        post(
            client,
            "/api/auth/login",
            {"email": "customer2@demo.invalid", "password": PASSWORD},
        ).status_code
        == 429
    )
    system.db.execute(
        "UPDATE AuthThrottle SET WindowEnd=DATE_SUB(UTC_TIMESTAMP(3),INTERVAL 1 MINUTE)"
    )
    assert (
        post(
            client,
            "/api/auth/login",
            {"email": "customer2@demo.invalid", "password": PASSWORD},
        ).status_code
        == 200
    )
    client.close()


def test_uc003_uc004_uc005_auto_assign_alert_and_no_automatic_reply(system):
    c = system.clients
    assert post(c["agent1"], "/api/presence").status_code == 200
    assert post(c["agent2"], "/api/presence").status_code == 200
    response = post(
        c["customer1"],
        "/api/tickets",
        {
            "title": "Tài khoản bức xúc",
            "content": "Tôi rất tức giận, cần trợ giúp tài khoản.",
        },
    )
    assert response.status_code == 201, response.text
    tid = response.json()["id"]
    row = system.db.fetch_one(
        "SELECT MaAgent,MucDoUuTien,TrangThai FROM Ticket WHERE MaTicket=?", (tid,)
    )
    assert (
        row["MaAgent"] is not None
        and row["MucDoUuTien"] == "Khẩn cấp"
        and row["TrangThai"] == "Mới"
    )
    assert (
        system.db.fetch_one(
            "SELECT COUNT(*) n FROM TicketReply WHERE MaTicket=?", (tid,)
        )["n"]
        == 0
    )
    assert system.db.fetch_one(
        "SELECT State,Sentiment FROM TicketAutomation WHERE MaTicket=?", (tid,)
    ) == {"State": "Done", "Sentiment": "Bức xúc cao"}
    alert = next(
        a
        for a in c["supervisor"].get("/api/supervisor/alerts").json()["alerts"]
        if a["sourceId"] == tid and a["source"] == "Ticket"
    )
    assert (
        post(
            c["customer1"], f"/api/supervisor/alerts/{alert['id']}/acknowledge"
        ).status_code
        == 403
    )
    assert (
        post(
            c["supervisor"], f"/api/supervisor/alerts/{alert['id']}/acknowledge"
        ).status_code
        == 200
    )
    automate_ticket(system.db, system.ai, tid, 1)
    assert (
        system.db.fetch_one(
            "SELECT COUNT(*) n FROM TicketAssignmentHistory WHERE MaTicket=?", (tid,)
        )["n"]
        == 1
    )


def test_uc002_uc006_uc009_uc010_chat_sentiment_handover_summary_rating(system):
    c = system.clients
    response = post(
        c["customer1"],
        "/api/chats",
        {"content": "Tôi bức xúc, xin hướng dẫn đăng nhập."},
    )
    assert response.status_code == 201, response.text
    chat = response.json()
    sid = chat["id"]
    analysis = system.db.fetch_one(
        "SELECT Sentiment FROM MessageAutomation WHERE MaMessage=?",
        (chat["messageId"],),
    )
    assert analysis["Sentiment"] == "Bức xúc cao"
    transfer = post(
        c["customer1"], f"/api/chats/{sid}/handover", {"reason": "Cần Agent hướng dẫn"}
    )
    assert transfer.status_code == 201, transfer.text
    assert transfer.json()["agentAvailable"] is True
    hid = transfer.json()["id"]
    h = system.db.fetch_one(
        "SELECT MaAgent,TomTat FROM Handover WHERE MaHandover=?", (hid,)
    )
    assert h["TomTat"]
    uid1 = system.db.fetch_one(
        "SELECT MaUser FROM UserAccount WHERE Email='agent1@demo.invalid'"
    )["MaUser"]
    agent = c["agent1" if h["MaAgent"] == uid1 else "agent2"]
    assert post(agent, f"/api/handovers/{hid}/accept").status_code == 200
    assert (
        post(
            agent,
            f"/api/handovers/{hid}/messages",
            {"content": "Agent đã tiếp nhận và hướng dẫn."},
        ).status_code
        == 201
    )
    assert post(agent, f"/api/handovers/{hid}/finish").status_code == 200
    assert post(c["customer1"], f"/api/chats/{sid}/close").status_code == 200
    assert (
        post(
            c["customer1"],
            f"/api/chats/{sid}/evaluation",
            {"stars": 5, "comment": "Đã hỗ trợ"},
        ).status_code
        == 201
    )
    assert (
        post(c["customer1"], f"/api/chats/{sid}/evaluation", {"stars": 4}).status_code
        == 409
    )
    assert (
        post(c["customer2"], f"/api/chats/{sid}/evaluation", {"stars": 5}).status_code
        == 404
    )
    assert c["customer1"].get(f"/api/chats/{sid}").json()["summary"]["content"]


def test_uc002_no_sources_fallback_and_masking_on_display(system):
    c = system.clients["customer1"]
    response = post(
        c,
        "/api/chats",
        {"content": "Câu ngoài nguồn. OTP 938471, CVV 391, CCCD 123456789012."},
    ).json()
    answer = post(
        c,
        f"/api/chats/{response['id']}/messages/{response['messageId']}/answer",
        {"language": "vi"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["status"] == "no_sources"
    detail = c.get(f"/api/chats/{response['id']}")
    assert all(
        secret not in detail.text for secret in ["938471", "391", "123456789012"]
    )
    assert (
        system.db.fetch_one(
            "SELECT NoiDung FROM Message WHERE MaMessage=?", (response["messageId"],)
        )["NoiDung"].find("938471")
        >= 0
    )
    assert (
        system.clients["customer2"].get(f"/api/chats/{response['id']}").status_code
        == 404
    )


def test_auto_failure_retains_ticket_and_supervisor_can_retry(system, monkeypatch):
    def fail(*args):
        raise RuntimeError("simulated provider failure")

    with monkeypatch.context() as patch:
        patch.setattr(system.ai, "classify_context", fail)
        response = post(
            system.clients["customer1"],
            "/api/tickets",
            {"title": "Ticket survives AI outage", "content": "Cần hỗ trợ đăng nhập."},
        )
        assert response.status_code == 201
    tid = response.json()["id"]
    assert (
        system.db.fetch_one(
            "SELECT State FROM TicketAutomation WHERE MaTicket=?", (tid,)
        )["State"]
        == "Failed"
    )
    assert (
        system.db.fetch_one("SELECT TrangThai FROM Ticket WHERE MaTicket=?", (tid,))[
            "TrangThai"
        ]
        == "Mới"
    )
    result = post(system.clients["supervisor"], f"/api/tickets/{tid}/automation/retry")
    assert result.status_code == 200, result.text
    assert (
        system.db.fetch_one(
            "SELECT State FROM TicketAutomation WHERE MaTicket=?", (tid,)
        )["State"]
        == "Done"
    )


def test_uc013_dashboard_all_required_groups_and_uc014_audit(system):
    result = system.clients["supervisor"].get("/api/reports/summary")
    assert result.status_code == 200
    data = result.json()
    assert all(
        data[key]
        for key in ["ticketsByStatus", "ticketsByPriority", "ticketsByCategory"]
    )
    assert data["chatSessions"] >= 8 and data["csat"]["total"] >= 16
    assert data["sla"]["overdueTickets"] > 0
    assert system.clients["admin"].get("/api/reports/summary").status_code == 403
    assert system.clients["customer1"].get("/api/admin/audit-logs").status_code == 403
    assert (
        system.clients["admin"]
        .get("/api/admin/audit-logs?action=DEMO_SEED")
        .json()["logs"]
    )


def test_no_online_agent_keeps_handover_in_queue(system):
    system.db.execute(
        "UPDATE AgentPresence SET LastSeen=DATE_SUB(UTC_TIMESTAMP(3),INTERVAL 5 MINUTE)"
    )
    chat = post(
        system.clients["customer1"], "/api/chats", {"content": "Cần tư vấn thêm."}
    ).json()
    response = post(
        system.clients["customer1"],
        f"/api/chats/{chat['id']}/handover",
        {"reason": "Chờ nhân viên"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["agentAvailable"] is False
    assert (
        system.db.fetch_one(
            "SELECT MaAgent FROM Handover WHERE MaHandover=?", (response.json()["id"],)
        )["MaAgent"]
        is None
    )


def test_uc007_uc008_uc016_agent_ticket_creation_human_review_and_correction(system):
    c = system.clients
    customer = system.db.fetch_one(
        "SELECT c.MaKH FROM Customer c JOIN UserAccount u ON u.MaUser=c.MaUser WHERE u.Email='customer1@demo.invalid'"
    )["MaKH"]
    for label in ["agent1", "agent2"]:
        post(c[label], "/api/presence")
    created = post(
        c["agent1"],
        "/api/tickets",
        {
            "customerId": customer,
            "title": "Tài khoản cần hướng dẫn",
            "content": "Hướng dẫn đăng nhập trong bản demo.",
        },
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]
    row = system.db.fetch_one("SELECT MaAgent FROM Ticket WHERE MaTicket=?", (tid,))
    first_id = system.db.fetch_one(
        "SELECT MaUser FROM UserAccount WHERE Email='agent1@demo.invalid'"
    )["MaUser"]
    agent = c["agent1" if row["MaAgent"] == first_id else "agent2"]
    assert post(agent, f"/api/tickets/{tid}/claim").status_code == 200
    analysis = post(agent, f"/api/tickets/{tid}/ai-assist", {"language": "vi"})
    assert analysis.status_code == 201, analysis.text
    aid = analysis.json()["id"]
    assert (
        system.db.fetch_one(
            "SELECT COUNT(*) n FROM TicketReply WHERE MaTicket=?", (tid,)
        )["n"]
        == 0
    )
    assert (
        post(
            agent,
            f"/api/tickets/{tid}/ai-assist/{aid}/review",
            {"decision": "selected"},
        ).status_code
        == 200
    )
    assert (
        system.db.fetch_one(
            "SELECT COUNT(*) n FROM TicketReply WHERE MaTicket=?", (tid,)
        )["n"]
        == 0
    )
    reply = post(
        agent,
        f"/api/tickets/{tid}/replies",
        {"content": "Đã kiểm tra và hướng dẫn khách hàng."},
    )
    rid = reply.json()["replyId"]
    correction = post(
        agent,
        f"/api/tickets/{tid}/replies",
        {"content": "Bổ sung hướng dẫn mới.", "correctionOf": rid},
    )
    assert correction.status_code == 200, correction.text
    assert (
        system.db.fetch_one("SELECT NoiDung FROM TicketReply WHERE MaReply=?", (rid,))[
            "NoiDung"
        ]
        == "Đã kiểm tra và hướng dẫn khách hàng."
    )
    assert (
        system.db.fetch_one(
            "SELECT CorrectionOf FROM TicketReply WHERE MaReply=?",
            (correction.json()["replyId"],),
        )["CorrectionOf"]
        == rid
    )
    assert (
        post(
            c["customer1"],
            f"/api/tickets/{tid}/replies",
            {"content": "Không được sửa thay Agent", "correctionOf": rid},
        ).status_code
        == 403
    )
    assert (
        post(
            c["supervisor"], f"/api/tickets/{tid}/priority", {"priority": "Cao"}
        ).status_code
        == 200
    )
    assert "chats" in c["supervisor"].get(f"/api/customers/{customer}").json()


def test_uc015_session_duration_and_read_audit(system):
    c = system.clients
    response = c["admin"].patch(
        "/api/admin/settings/auth.session_hours",
        json={"value": 2},
        headers={"Origin": "http://localhost:3000", "X-Vietincare-Request": "1"},
    )
    assert response.status_code == 200, response.text
    isolated = TestClient(
        system.app, base_url=system.settings.origin, client=("127.0.0.43", 41000)
    )
    result = post(
        isolated,
        "/api/auth/login",
        {"email": "customer3@demo.invalid", "password": PASSWORD},
    )
    assert result.status_code == 200, result.text
    assert "Max-Age=7200" in result.headers["set-cookie"]
    assert isolated.get("/api/tickets").status_code == 200
    assert (
        system.db.fetch_one(
            "SELECT COUNT(*) n FROM AuditLog WHERE HanhDong='ACCESS_READ'"
        )["n"]
        > 0
    )
    isolated.close()


def test_chat_append_only_correction_rejects_other_conversation(system):
    c = system.clients["customer1"]
    a = post(c, "/api/chats", {"content": "Tin gốc cần bổ sung."}).json()
    b = post(c, "/api/chats", {"content": "Hội thoại khác."}).json()
    bad = post(
        c,
        f"/api/chats/{b['id']}/messages",
        {"content": "Sai hội thoại", "correctionOf": a["messageId"]},
    )
    assert bad.status_code == 403
    fixed = post(
        c,
        f"/api/chats/{a['id']}/messages",
        {"content": "Bản đính chính.", "correctionOf": a["messageId"]},
    )
    assert fixed.status_code == 200, fixed.text
    assert (
        system.db.fetch_one(
            "SELECT NoiDung FROM Message WHERE MaMessage=?", (a["messageId"],)
        )["NoiDung"]
        == "Tin gốc cần bổ sung."
    )


def test_runtime_account_has_no_ddl_permissions(system):
    with pytest.raises(mysql.connector.Error):
        system.db.execute("CREATE TABLE ShouldNotBeAllowed(id INT)")


def test_handover_pagination_preserves_full_history_and_sentiment(system):
    owner = system.db.fetch_one(
        "SELECT c.MaKH,u.MaUser FROM Customer c JOIN UserAccount u ON u.MaUser=c.MaUser WHERE u.Email='customer1@demo.invalid'"
    )
    with system.db.transaction() as tx:
        sid = tx.execute(
            "INSERT INTO ChatSession(MaKH,TieuDe) VALUES(?,'Long conversation acceptance')",
            (owner["MaKH"],),
        )
        ids = []
        for i in range(205):
            ids.append(
                tx.execute(
                    "INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",
                    (sid, owner["MaUser"], f"Message {i+1}"),
                )
            )
        hid = tx.execute(
            "INSERT INTO Handover(MaSession,LyDo) VALUES(?,'Pagination test')", (sid,)
        )
        tx.execute(
            "INSERT INTO MessageAutomation(MaMessage,State,Sentiment) VALUES(?,'Done','Bức xúc cao')",
            (ids[-1],),
        )
    seen = []
    cursor = None
    while True:
        r = system.clients["supervisor"].get(
            f"/api/handovers/{hid}", params={"before": cursor} if cursor else {}
        )
        assert r.status_code == 200, r.text
        data = r.json()
        seen.extend(m["id"] for m in data["messages"])
        cursor = data["next"]
        if not cursor:
            break
    assert sorted(seen) == ids and len(set(seen)) == 205


def test_five_sessions_fifty_questions_thousand_chunks_simulated_provider(system):
    from backend.ai import _unit_embedding

    _unit_embedding.cache_clear()

    def worker(index):
        client = TestClient(
            system.app,
            base_url=system.settings.origin,
            client=(f"127.0.1.{index+1}", 45000),
        )
        login = post(
            client,
            "/api/auth/login",
            {"email": f"customer{index%4+1}@demo.invalid", "password": PASSWORD},
        )
        assert login.status_code == 200
        times = []
        for n in range(10):
            started = time.perf_counter()
            chat = post(
                client,
                "/api/chats",
                {"content": f"Hướng dẫn đăng nhập demo {index}-{n}"},
            )
            assert chat.status_code == 201, chat.text
            data = chat.json()
            result = post(
                client,
                f"/api/chats/{data['id']}/messages/{data['messageId']}/answer",
                {"language": "vi"},
            )
            assert result.status_code == 200, result.text
            assert result.json()["status"] == "answered"
            times.append(time.perf_counter() - started)
        client.close()
        return times

    with ThreadPoolExecutor(max_workers=5) as pool:
        timings = [t for group in pool.map(worker, range(5)) for t in group]
    timings.sort()
    report = {
        "provider": "SIMULATION, not live Gemini",
        "questions": 50,
        "concurrent_sessions": 5,
        "knowledge_chunks": 1000,
        "p95_seconds": round(timings[47], 4),
        "errors": 0,
        "target_seconds": 5,
        "live_provider_acceptance": "NOT_VERIFIED",
    }
    path = Path("docs/reports/final-acceptance-20261029")
    path.mkdir(parents=True, exist_ok=True)
    (path / "performance-simulation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    assert len(timings) == 50 and all(t > 0 for t in timings)
    # Gate the local demo target while explicitly leaving the live-provider SLA unverified.
    assert timings[47] <= 5, f"Local demo p95 exceeded 5 seconds: {timings[47]:.4f}"
