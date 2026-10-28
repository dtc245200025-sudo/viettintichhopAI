import os
import re
import secrets
import uuid
from dataclasses import replace
from typing import Any

import mysql.connector
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.db import Database
from backend.migrations import migrate
from backend.security import hash_password


pytestmark = pytest.mark.skipif(os.environ.get("RUN_MYSQL_TESTS") != "1", reason="requires an isolated MySQL 8.0.46 admin connection")


class FakeAI:
    enabled = True
    provider = "gemini"
    model = "gemini-embedding-001"
    dimensions = 768

    def embed(self, texts: list[str], purpose: str = "document") -> list[list[float]]:
        return [[1.0] + [0.0] * (self.dimensions - 1) for _ in texts]

    def answer(self, question: str, sources: list[dict[str, Any]], language: str) -> dict[str, Any]:
        return {"text": "Published support instructions.", "sourceIds": [sources[0]["id"]]}

    def support_assist(self, context: dict[str, Any], language: str = "vi") -> dict[str, str]:
        return {
            "category": "Đăng nhập",
            "priority": "Cao",
            "sentiment": "Tiêu cực",
            "draftReply": "Đây là bản nháp cần nhân viên duyệt.",
            "summary": "Khách cần hỗ trợ đăng nhập.",
        }


def _connect_options(settings: Settings) -> dict[str, object]:
    return {key: value for key, value in settings.database.items() if key != "database"}


def _post(client: TestClient, origin: str, path: str, payload: dict[str, Any], key: str | None = None):
    return client.post(
        path,
        json=payload,
        headers={
            "Origin": origin,
            "X-Vietincare-Request": "1",
            "Idempotency-Key": key or str(uuid.uuid4()),
        },
    )


def test_isolated_mysql_migration_admin_assignment_and_support_flow() -> None:
    base_settings = Settings.from_env()
    database_name = f"vietincare_py_test_{secrets.token_hex(6)}"
    assert re.fullmatch(r"vietincare_py_test_[0-9a-f]{12}", database_name)
    settings = replace(base_settings, database={**base_settings.database, "database": database_name})
    admin = mysql.connector.connect(**_connect_options(settings))
    database: Database | None = None
    created = False
    try:
        cursor = admin.cursor(dictionary=True)
        try:
            cursor.execute("SELECT VERSION() version")
            version = cursor.fetchone()["version"]
        finally:
            cursor.close()
        if not str(version).startswith("8.0.46"):
            raise RuntimeError("This test requires MySQL Community Server 8.0.46")
        cursor = admin.cursor()
        try:
            cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            admin.commit()
            created = True
        finally:
            cursor.close()
        migration_result = migrate(settings, initialize=True)
        assert migration_result == {"status": "applied", "steps": 33}
        assert migrate(settings, check=True) == {"status": "current", "steps": 33}

        connection = mysql.connector.connect(**settings.database)
        cursor = connection.cursor(dictionary=True)
        password = "Isolated-MySQL-Test-2026!"
        password_hash = hash_password(password)
        identities: dict[str, tuple[int, int | None]] = {}
        for role_name in ("Customer", "Agent", "Supervisor", "Admin"):
            cursor.execute("SELECT MaRole FROM Role WHERE TenRole=%s", (role_name,))
            role = cursor.fetchone()
            assert role is not None
            email = f"{role_name.lower()}@example.test"
            username = f"{role_name.lower()}_{secrets.token_hex(6)}"
            cursor.execute(
                "INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) VALUES(%s,%s,%s,%s,%s)",
                (role["MaRole"], role_name, username, email, password_hash),
            )
            user_id = int(cursor.lastrowid)
            customer_id = None
            if role_name == "Customer":
                cursor.execute("INSERT INTO Customer(MaUser,HoTen,Email) VALUES(%s,%s,%s)", (user_id, role_name, email))
                customer_id = int(cursor.lastrowid)
            identities[role_name] = (user_id, customer_id)
        connection.commit()
        cursor.close()
        connection.close()

        database = Database(settings.database)
        app = create_app(database=database, settings=settings, ai=FakeAI())
        with TestClient(app, base_url=settings.origin) as client:
            logins = {}
            for role_name in identities:
                client.cookies.clear()
                response = _post(client, settings.origin, "/api/auth/login", {
                    "email": f"{role_name.lower()}@example.test",
                    "password": password,
                })
                assert response.status_code == 200, response.text
                logins[role_name] = client.cookies.get("vietincare_session")
                assert logins[role_name]

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Customer"])
            key = str(uuid.uuid4())
            first_ticket = _post(client, settings.origin, "/api/tickets", {
                "title": "Login assistance",
                "content": "Customer cannot sign in.",
            }, key)
            retry_ticket = _post(client, settings.origin, "/api/tickets", {
                "title": "Login assistance",
                "content": "Customer cannot sign in.",
            }, key)
            assert first_ticket.status_code == 201
            assert retry_ticket.status_code == 200
            ticket_id = first_ticket.json()["id"]
            assert retry_ticket.json()["id"] == ticket_id

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Supervisor"])
            agents = client.get("/api/tickets/agents")
            assert agents.status_code == 200
            assert len(agents.json()["agents"]) == 1
            assignment = _post(client, settings.origin, f"/api/tickets/{ticket_id}/assign", {"agentId": identities["Agent"][0]})
            assert assignment.status_code == 200, assignment.text
            assert assignment.json()["status"] == "Mới"

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Agent"])
            claim = _post(client, settings.origin, f"/api/tickets/{ticket_id}/claim", {})
            assert claim.status_code == 200, claim.text
            edited = _post(client, settings.origin, f"/api/tickets/{ticket_id}/details", {
                "title": "Updated login assistance", "content": "Updated support description", "categoryId": None,
            })
            assert edited.status_code == 200, edited.text
            assert client.get(f"/api/tickets/{ticket_id}").json()["ticket"]["title"] == "Updated login assistance"
            analysis = _post(client, settings.origin, f"/api/tickets/{ticket_id}/ai-assist", {"language": "en"})
            assert analysis.status_code == 201, analysis.text
            assert analysis.json()["requiresHumanReview"] is True
            assert analysis.json()["status"] == "Pending"
            saved = client.get(f"/api/tickets/{ticket_id}").json()["analyses"]
            assert saved[0]["summary"] == analysis.json()["summary"]
            review = _post(client, settings.origin, f"/api/tickets/{ticket_id}/ai-assist/{analysis.json()['id']}/review", {"decision": "selected"})
            assert review.status_code == 200
            assert _post(client, settings.origin, f"/api/tickets/{ticket_id}/replies", {
                "content": analysis.json()["draftReply"],
            }).status_code == 200
            assert _post(client, settings.origin, f"/api/tickets/{ticket_id}/status", {"status": "Chờ khách hàng"}).status_code == 200
            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Customer"])
            assert _post(client, settings.origin, f"/api/tickets/{ticket_id}/replies", {"content": "Additional details."}).status_code == 200
            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Agent"])
            assert _post(client, settings.origin, f"/api/tickets/{ticket_id}/status", {"status": "Đã đóng"}).status_code == 200

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Customer"])
            rating = _post(client, settings.origin, f"/api/tickets/{ticket_id}/evaluation", {"stars": 5, "comment": "Helpful"})
            assert rating.status_code == 201, rating.text
            assert _post(client, settings.origin, f"/api/tickets/{ticket_id}/evaluation", {"stars": 4}).status_code == 409
            detail = client.get(f"/api/tickets/{ticket_id}")
            assert detail.status_code == 200
            assert detail.json()["evaluation"]["stars"] == 5

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Supervisor"])
            customer_id = identities['Customer'][1]
            assert client.get('/api/customers?query=Customer').status_code == 200
            customer_history = client.get(f'/api/customers/{customer_id}')
            assert customer_history.json()['tickets'][0]['id'] == ticket_id
            contact = client.patch(f'/api/customers/{customer_id}', json={'fullName': 'Updated Customer'}, headers={
                'Origin': settings.origin, 'X-Vietincare-Request': '1',
            })
            assert contact.status_code == 200, contact.text
            assert client.get(f'/api/customers/{customer_id}').json()['customer']['name'] == 'Updated Customer'
            report = client.get("/api/reports/summary")
            assert report.status_code == 200, report.text
            assert report.json()["csat"]["satisfactionPercent"] == 100.0
            assert report.json()["resolution"]["closedTickets"] == 1

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Admin"])
            managed_user = _post(client, settings.origin, "/api/admin/users", {
                "fullName": "Managed Customer",
                "email": f"managed_{secrets.token_hex(4)}@example.test",
                "phone": "+84901234567",
                "role": "Customer",
                "password": password,
            })
            assert managed_user.status_code == 201, managed_user.text
            managed_users = client.get("/api/admin/users?role=Customer")
            assert managed_users.status_code == 200
            assert any(user["id"] == managed_user.json()["id"] for user in managed_users.json()["users"])
            document = _post(client, settings.origin, "/api/knowledge", {
                "title": "Support guide",
                "content": "Published instructions for account access.",
            })
            assert document.status_code == 201, document.text
            document_id = document.json()["id"]
            assert _post(client, settings.origin, f"/api/knowledge/{document_id}/index", {"version": 1}).status_code == 200
            assert _post(client, settings.origin, f"/api/knowledge/{document_id}/publish", {"version": 1}).status_code == 200

            client.cookies.clear()
            client.cookies.set("vietincare_session", logins["Customer"])
            chat = _post(client, settings.origin, "/api/chats", {"content": "How can I access my account?"})
            assert chat.status_code == 201, chat.text
            answer = _post(client, settings.origin, f"/api/chats/{chat.json()['id']}/messages/{chat.json()['messageId']}/answer", {"language": "en"})
            assert answer.status_code == 200, answer.text
            history = client.get(f"/api/chats/{chat.json()['id']}")
            assert history.status_code == 200
            assert any(message.get("sources") for message in history.json()["messages"] if message["sender"] == "AI")
    finally:
        if database is not None:
            pool = database.pool
            remove_connections = getattr(pool, "_remove_connections", None)
            if callable(remove_connections):
                remove_connections()
        if created:
            cursor = admin.cursor()
            try:
                cursor.execute(f"DROP DATABASE `{database_name}`")
            finally:
                cursor.close()
        admin.close()
