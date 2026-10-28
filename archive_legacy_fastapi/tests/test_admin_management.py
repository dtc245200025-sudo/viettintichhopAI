from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


class FakeTransaction:
    def __init__(self, database: "FakeAdminDatabase") -> None:
        self.database = database

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()):
        if "SELECT MaRole FROM Role" in statement:
            return {"MaRole": {"Customer": 1, "Agent": 2, "Supervisor": 3, "Admin": 4}[parameters[0]]}
        if "WHERE u.MaUser=? FOR UPDATE" in statement:
            return self.database.target_user
        if "SELECT MaKH,TrangThai FROM Customer" in statement:
            return None
        return None

    def fetch_all(self, statement: str, parameters: tuple[object, ...] = ()):
        if "r.TenRole='Admin' AND u.TrangThai=1" in statement:
            return self.database.active_admins
        return []

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> int:
        self.database.executed.append((statement, parameters))
        if statement.startswith("INSERT INTO UserAccount"):
            self.database.created_password_hash = str(parameters[3])
            return 28
        return 1


class FakeAdminDatabase:
    def __init__(self, role: str = "Admin") -> None:
        self.role = role
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.created_password_hash = ""
        self.list_query = ""
        self.list_parameters: tuple[object, ...] = ()
        self.target_user = {"id": 8, "name": "Other Admin", "email": "other@example.test", "phone": None, "isActive": 1, "roleId": 4, "role": "Admin"}
        self.active_admins = [{"MaUser": 4}]

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()):
        return {
            "MaUser": 4,
            "HoTen": "Administrator",
            "Email": "admin@example.test",
            "TenRole": self.role,
            "MaKH": None,
        }

    def fetch_all(self, statement: str, parameters: tuple[object, ...] = ()):
        self.list_query = statement
        self.list_parameters = parameters
        return [{"id": 28, "name": "Customer", "email": "customer@example.test", "phone": None, "role": "Customer", "isActive": 1}]

    @contextmanager
    def transaction(self):
        yield FakeTransaction(self)


def _client(database: FakeAdminDatabase) -> tuple[TestClient, dict[str, str]]:
    settings = Settings.from_env({"APP_ORIGIN": "http://localhost:3000"})
    client = TestClient(create_app(database=database, settings=settings))
    client.cookies.set("vietincare_session", "a" * 64)
    return client, {"Origin": settings.origin, "X-Vietincare-Request": "1"}


def test_admin_user_list_is_admin_only_and_does_not_select_password_hashes() -> None:
    admin_db = FakeAdminDatabase()
    client, _ = _client(admin_db)

    response = client.get("/api/admin/users?role=Customer&query=customer")

    assert response.status_code == 200
    assert response.json()["users"][0]["email"] == "customer@example.test"
    assert "PasswordHash" not in admin_db.list_query
    supervisor, _ = _client(FakeAdminDatabase("Supervisor"))
    denied = supervisor.get("/api/admin/users")
    assert denied.status_code == 403
    assert denied.json() == {"error": "FORBIDDEN"}


def test_admin_user_list_uses_cursor_and_rejects_invalid_role_values() -> None:
    database = FakeAdminDatabase()
    client, _ = _client(database)

    page = client.get("/api/admin/users?before=27")
    invalid_role = client.get("/api/admin/users?role=Unknown")
    invalid_cursor = client.get("/api/admin/users?before=not-a-number")

    assert page.status_code == 200
    assert page.json()["limit"] == 50
    assert page.json()["next"] is None
    assert "u.MaUser<?" in database.list_query
    assert database.list_parameters[-1] == 27
    assert invalid_role.status_code == 400
    assert invalid_cursor.status_code == 400


def test_admin_creates_customer_and_stores_only_hashed_password() -> None:
    database = FakeAdminDatabase()
    client, headers = _client(database)

    response = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "fullName": "New Customer",
            "email": "new@example.test",
            "phone": "+84901234567",
            "role": "Customer",
            "password": "a-strong-test-password",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"id": 28, "message": "USER_CREATED"}
    assert database.created_password_hash.startswith("scrypt$32768$8$1$")
    assert database.created_password_hash != "a-strong-test-password"
    assert any(statement.startswith("INSERT INTO Customer") for statement, _ in database.executed)
    assert any(statement.startswith("INSERT INTO AuditLog") for statement, _ in database.executed)


def test_admin_cannot_demote_last_active_admin_or_disable_self() -> None:
    database = FakeAdminDatabase()
    client, headers = _client(database)

    last_admin = client.patch("/api/admin/users/8", headers=headers, json={"role": "Supervisor"})
    self_disable = client.patch("/api/admin/users/4", headers=headers, json={"isActive": False})

    assert last_admin.status_code == 409
    assert last_admin.json() == {"error": "LAST_ACTIVE_ADMIN"}
    assert self_disable.status_code == 409
    assert self_disable.json() == {"error": "CANNOT_CHANGE_SELF_ROLE"}


def test_admin_updates_role_status_and_password_with_session_revocation() -> None:
    database = FakeAdminDatabase()
    database.target_user["role"] = "Agent"
    client, headers = _client(database)

    response = client.patch(
        "/api/admin/users/8",
        headers=headers,
        json={
            "fullName": "Updated Agent",
            "email": "updated@example.test",
            "phone": "+84901234567",
            "role": "Supervisor",
            "isActive": False,
            "password": "replacement-password-123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"id": 8, "message": "USER_UPDATED"}
    update = next(item for item in database.executed if item[0].startswith("UPDATE UserAccount"))
    assert update[1][0] == 3
    assert update[1][4] is False
    assert str(update[1][5]).startswith("scrypt$32768$8$1$")
    assert any(statement.startswith("DELETE FROM AuthSession") for statement, _ in database.executed)
    assert any(statement.startswith("INSERT INTO AuditLog") for statement, _ in database.executed)