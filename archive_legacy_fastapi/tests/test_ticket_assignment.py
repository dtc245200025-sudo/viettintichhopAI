from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


class FakeAssignmentTransaction:
    def __init__(self, database: "FakeAssignmentDatabase") -> None:
        self.database = database

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()):
        if "SELECT TrangThai FROM UserAccount" in statement:
            return {"TrangThai": 1}
        if "SELECT RequestHash,Result FROM TicketRequest" in statement:
            return None
        if "SELECT MaAgent,TrangThai FROM Ticket WHERE" in statement:
            return {"MaAgent": self.database.ticket["agentId"], "TrangThai": self.database.ticket["status"]}
        if "FROM Ticket t WHERE t.MaTicket=?" in statement and "FOR UPDATE" in statement:
            return self.database.ticket
        if "SELECT u.MaUser FROM UserAccount u JOIN Role" in statement:
            return {"MaUser": 12} if int(parameters[0]) == 12 and self.database.agent_active else None
        return None

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> int:
        self.database.executed.append((statement, parameters))
        return 21


class FakeAssignmentDatabase:
    def __init__(self, role: str = "Supervisor", *, status: str = "Mới", agent_id: int | None = None, agent_active: bool = True) -> None:
        self.role = role
        self.agent_active = agent_active
        self.ticket = {
            "id": 31,
            "customerId": 5,
            "agentId": agent_id,
            "title": "Login issue",
            "status": status,
            "priority": "Trung bình",
            "createdAt": None,
            "updatedAt": None,
            "closedAt": None,
            "content": "Cannot sign in",
        }
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()):
        user_id = 12 if self.role == "Agent" else 4
        return {"MaUser": user_id, "HoTen": self.role, "Email": f"{self.role.lower()}@example.test", "TenRole": self.role, "MaKH": None}

    def fetch_all(self, statement: str, parameters: tuple[object, ...] = ()):
        if "JOIN Role r" in statement and "r.TenRole='Agent'" in statement:
            return [{"id": 12, "name": "Agent One", "email": "agent@example.test"}]
        return []

    @contextmanager
    def transaction(self):
        yield FakeAssignmentTransaction(self)


def _client(database: FakeAssignmentDatabase) -> tuple[TestClient, dict[str, str]]:
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings))
    client.cookies.set("vietincare_session", "b" * 64)
    return client, {"Origin": settings.origin, "X-Vietincare-Request": "1"}


def test_supervisor_can_list_active_agents_and_assign_without_starting_ticket() -> None:
    database = FakeAssignmentDatabase()
    client, headers = _client(database)
    agents = client.get("/api/tickets/agents")

    response = client.post(
        "/api/tickets/31/assign",
        headers={**headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abc"},
        json={"agentId": 12},
    )

    assert agents.status_code == 200
    assert agents.json()["agents"][0]["id"] == 12
    assert response.status_code == 200
    assert response.json() == {"id": 31, "agentId": 12, "status": "Mới"}
    assert any(statement.startswith("INSERT INTO TicketAssignmentHistory") for statement, _ in database.executed)
    assert any(statement.startswith("INSERT INTO TicketRequest") for statement, _ in database.executed)


def test_non_supervisor_cannot_assign_and_inactive_agents_are_rejected() -> None:
    agent_client, headers = _client(FakeAssignmentDatabase("Agent"))
    denied = agent_client.post(
        "/api/tickets/31/assign",
        headers={**headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abc"},
        json={"agentId": 12},
    )
    assert denied.status_code == 403

    inactive_client, inactive_headers = _client(FakeAssignmentDatabase(agent_active=False))
    rejected = inactive_client.post(
        "/api/tickets/31/assign",
        headers={**inactive_headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abd"},
        json={"agentId": 12},
    )
    assert rejected.status_code == 400
    assert rejected.json() == {"error": "AGENT_NOT_AVAILABLE"}


def test_supervisor_cannot_assign_completed_ticket() -> None:
    client, headers = _client(FakeAssignmentDatabase(status="Đã đóng"))

    response = client.post(
        "/api/tickets/31/assign",
        headers={**headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abc"},
        json={"agentId": 12},
    )

    assert response.status_code == 409
    assert response.json() == {"error": "TICKET_READ_ONLY"}


def test_supervisor_can_reassign_an_in_progress_ticket_and_records_both_agents() -> None:
    database = FakeAssignmentDatabase(status="Đang xử lý", agent_id=13)
    client, headers = _client(database)

    response = client.post(
        "/api/tickets/31/assign",
        headers={**headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abe"},
        json={"agentId": 12},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Đang xử lý"
    history_insert = next(item for item in database.executed if item[0].startswith("INSERT INTO TicketAssignmentHistory"))
    assert history_insert[1] == (31, 13, 12, 4)


def test_only_assigned_agent_can_accept_a_new_ticket() -> None:
    assigned_database = FakeAssignmentDatabase("Agent", agent_id=12)
    assigned_client, headers = _client(assigned_database)
    accepted = assigned_client.post(
        "/api/tickets/31/claim",
        headers={**headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abc"},
        json={},
    )
    assert accepted.status_code == 200
    assert any(statement.startswith("UPDATE Ticket SET MaAgent") for statement, _ in assigned_database.executed)

    other_client, other_headers = _client(FakeAssignmentDatabase("Agent", agent_id=13))
    rejected = other_client.post(
        "/api/tickets/31/claim",
        headers={**other_headers, "Idempotency-Key": "12345678-1234-4234-8234-123456789abd"},
        json={},
    )
    assert rejected.status_code == 409
    assert rejected.json() == {"error": "TICKET_ALREADY_CLAIMED"}