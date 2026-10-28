import secrets
from typing import Any

import mysql.connector.errors
from fastapi import FastAPI, Request

from backend.auth import EMAIL_RE, PHONE_RE, ROLES, _cookie_token, _require_role, current_user
from backend.db import Database, Transaction
from backend.errors import ApiError
from backend.security import digest, hash_password


def _user_fields(payload: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    allowed = {"fullName", "email", "phone", "role", "isActive", "password"}
    if payload.keys() - allowed or (creating and not {"fullName", "email", "role", "password"}.issubset(payload)):
        raise ApiError(400, "INVALID_INPUT")
    values: dict[str, Any] = {}
    if "fullName" in payload:
        name = payload["fullName"]
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise ApiError(400, "INVALID_INPUT")
        values["name"] = name.strip()
    if "email" in payload:
        email = payload["email"]
        if not isinstance(email, str) or not EMAIL_RE.fullmatch(email.strip()) or len(email.strip()) > 100:
            raise ApiError(400, "INVALID_INPUT")
        values["email"] = email.strip().lower()
    if "phone" in payload:
        phone = payload["phone"]
        if phone is None:
            values["phone"] = None
        elif isinstance(phone, str) and (not phone.strip() or PHONE_RE.fullmatch(phone.strip())) and len(phone.strip()) <= 20:
            values["phone"] = phone.strip() or None
        else:
            raise ApiError(400, "INVALID_INPUT")
    if "role" in payload:
        if not isinstance(payload["role"], str) or payload["role"] not in ROLES:
            raise ApiError(400, "INVALID_INPUT")
        values["role"] = payload["role"]
    if "isActive" in payload:
        if type(payload["isActive"]) is not bool:
            raise ApiError(400, "INVALID_INPUT")
        values["active"] = payload["isActive"]
    if "password" in payload:
        password = payload["password"]
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ApiError(400, "INVALID_INPUT")
        values["passwordHash"] = hash_password(password)
    if not values:
        raise ApiError(400, "INVALID_INPUT")
    return values


def install_admin_routes(app: FastAPI, database: Database) -> None:
    @app.get("/api/admin/users")
    def list_users(request: Request, role: str | None = None, query: str | None = None, before: str | None = None) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        if role is not None and role not in ROLES:
            raise ApiError(400, "INVALID_INPUT")
        if query is not None and len(query.strip()) > 100:
            raise ApiError(400, "INVALID_INPUT")
        cursor = int(before) if before is not None and before.isdecimal() and 1 <= int(before) <= 2147483647 else None
        if before is not None and cursor is None:
            raise ApiError(400, "INVALID_INPUT")
        filters = []
        parameters: list[object] = []
        if role:
            filters.append("r.TenRole=?")
            parameters.append(role)
        if query and query.strip():
            filters.append("(u.HoTen LIKE ? OR u.Email LIKE ? OR u.SoDienThoai LIKE ?)")
            search = f"%{query.strip()}%"
            parameters.extend((search, search, search))
        filters.append("u.MaUser<?")
        parameters.append(cursor if cursor is not None else 2147483647)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        users = database.fetch_all(
            "SELECT u.MaUser id,u.HoTen name,u.Email email,u.SoDienThoai phone,r.TenRole role,"
            f"u.TrangThai isActive,u.NgayTao createdAt FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole {where} "
            "ORDER BY u.MaUser DESC LIMIT 51",
            tuple(parameters),
        )
        has_more = len(users) > 50
        page = users[:50]
        return {"users": page, "limit": 50, "next": page[-1]["id"] if has_more and page else None}

    @app.post("/api/admin/users", status_code=201)
    def create_user(payload: dict[str, Any], request: Request) -> dict[str, Any]:
        actor = current_user(request, database)
        _require_role(actor, "Admin")
        values = _user_fields(payload, creating=True)
        password_hash = values.pop("passwordHash")
        try:
            with database.transaction() as transaction:
                role = transaction.fetch_one("SELECT MaRole FROM Role WHERE TenRole=?", (values["role"],))
                if not role:
                    raise RuntimeError("Database roles are not initialized")
                user_id = transaction.execute(
                    "INSERT INTO UserAccount(MaRole,HoTen,Username,PasswordHash,Email,SoDienThoai) VALUES(?,?,?,?,?,?)",
                    (
                        role["MaRole"], values["name"], f"admin_{secrets.token_hex(16)}", password_hash,
                        values["email"], values.get("phone"),
                    ),
                )
                if values["role"] == "Customer":
                    transaction.execute(
                        "INSERT INTO Customer(MaUser,HoTen,Email,SoDienThoai,LoaiKhachHang) VALUES(?,?,?,?,?)",
                        (user_id, values["name"], values["email"], values.get("phone"), "Cá nhân"),
                    )
                transaction.execute(
                    "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'UserAccount',?,?)",
                    (actor["MaUser"], "ADMIN_USER_CREATE", user_id, request.client.host if request.client else None),
                )
        except mysql.connector.errors.IntegrityError as error:
            if error.errno == 1062:
                raise ApiError(409, "EMAIL_EXISTS") from error
            raise
        return {"id": user_id, "message": "USER_CREATED"}

    @app.patch("/api/admin/users/{user_id}")
    def update_user(user_id: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        actor = current_user(request, database)
        _require_role(actor, "Admin")
        if not user_id.isdecimal() or not 1 <= int(user_id) <= 2147483647:
            raise ApiError(400, "INVALID_INPUT")
        target_id = int(user_id)
        values = _user_fields(payload, creating=False)
        try:
            with database.transaction() as transaction:
                target = transaction.fetch_one(
                    "SELECT u.MaUser id,u.HoTen name,u.Email email,u.SoDienThoai phone,u.TrangThai isActive,"
                    "r.MaRole roleId,r.TenRole role FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole "
                    "WHERE u.MaUser=? FOR UPDATE",
                    (target_id,),
                )
                if not target:
                    raise ApiError(404, "USER_NOT_FOUND")
                new_role = values.get("role", target["role"])
                new_active = values.get("active", bool(target["isActive"]))
                if target_id == actor["MaUser"] and (new_role != "Admin" or not new_active):
                    raise ApiError(409, "CANNOT_CHANGE_SELF_ROLE")
                if target["role"] == "Admin" and target["isActive"] and (new_role != "Admin" or not new_active):
                    admins = transaction.fetch_all(
                        "SELECT u.MaUser FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole "
                        "WHERE r.TenRole='Admin' AND u.TrangThai=1 FOR UPDATE"
                    )
                    if len(admins) <= 1:
                        raise ApiError(409, "LAST_ACTIVE_ADMIN")
                role = transaction.fetch_one("SELECT MaRole FROM Role WHERE TenRole=?", (new_role,))
                if not role:
                    raise RuntimeError("Database roles are not initialized")
                name = values.get("name", target["name"])
                email = values.get("email", target["email"])
                phone = values.get("phone", target["phone"])
                password_hash = values.get("passwordHash")
                if password_hash is None:
                    transaction.execute(
                        "UPDATE UserAccount SET MaRole=?,HoTen=?,Email=?,SoDienThoai=?,TrangThai=? WHERE MaUser=?",
                        (role["MaRole"], name, email, phone, new_active, target_id),
                    )
                else:
                    transaction.execute(
                        "UPDATE UserAccount SET MaRole=?,HoTen=?,Email=?,SoDienThoai=?,TrangThai=?,PasswordHash=? WHERE MaUser=?",
                        (role["MaRole"], name, email, phone, new_active, password_hash, target_id),
                    )
                customer = transaction.fetch_one("SELECT MaKH,TrangThai FROM Customer WHERE MaUser=? FOR UPDATE", (target_id,))
                if new_role == "Customer" and not customer:
                    transaction.execute(
                        "INSERT INTO Customer(MaUser,HoTen,Email,SoDienThoai,LoaiKhachHang,TrangThai) VALUES(?,?,?,?,?,?)",
                        (target_id, name, email, phone, "Cá nhân", new_active),
                    )
                elif customer:
                    transaction.execute(
                        "UPDATE Customer SET HoTen=?,Email=?,SoDienThoai=?,TrangThai=? WHERE MaUser=?",
                        (name, email, phone, new_active if new_role == "Customer" else customer.get("TrangThai", 1), target_id),
                    )
                current_token = _cookie_token(request) if target_id == actor["MaUser"] else None
                if current_token:
                    transaction.execute(
                        "DELETE FROM AuthSession WHERE MaUser=? AND TokenHash<>?",
                        (target_id, digest(current_token)),
                    )
                else:
                    transaction.execute("DELETE FROM AuthSession WHERE MaUser=?", (target_id,))
                transaction.execute("DELETE FROM AuthOtpChallenge WHERE MaUser=?", (target_id,))
                transaction.execute(
                    "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'UserAccount',?,?)",
                    (actor["MaUser"], "ADMIN_USER_UPDATE", target_id, request.client.host if request.client else None),
                )
        except mysql.connector.errors.IntegrityError as error:
            if error.errno == 1062:
                raise ApiError(409, "EMAIL_EXISTS") from error
            raise
        return {"id": target_id, "message": "USER_UPDATED"}