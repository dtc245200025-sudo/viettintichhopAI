"""Customer contacts and support history for authorized staff."""

from typing import Any

import mysql.connector.errors
from fastapi import FastAPI, Request

from backend.admin import _user_fields
from backend.auth import _require_role, current_user
from backend.db import Database
from backend.errors import ApiError
from backend.tickets import numeric_id

FIELDS = "c.MaKH id,c.MaUser userId,c.HoTen name,c.Email email,c.SoDienThoai phone,c.TrangThai isActive"


def install_customer_routes(app: FastAPI, database: Database) -> None:
    @app.get("/api/customers")
    def list_customers(
        request: Request, query: str = "", before: str | None = None
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin", "Supervisor")
        if len(query.strip()) > 100:
            raise ApiError(400, "INVALID_INPUT")
        cursor = numeric_id(before) if before is not None else 2147483647
        search = "%" + query.strip() + "%"
        rows = database.fetch_all(
            f"SELECT {FIELDS} FROM Customer c WHERE c.MaKH<? "
            "AND (c.HoTen LIKE ? OR c.Email LIKE ? OR c.SoDienThoai LIKE ?) ORDER BY c.MaKH DESC LIMIT 51",
            (cursor, search, search, search),
        )
        return {
            "customers": rows[:50],
            "next": rows[49]["id"] if len(rows) > 50 else None,
        }

    @app.get("/api/customers/{customer_id}")
    def customer_detail(
        customer_id: str, request: Request, before: str | None = None
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin", "Supervisor")
        parsed_id = numeric_id(customer_id)
        cursor = numeric_id(before) if before is not None else 2147483647
        customer = database.fetch_one(
            f"SELECT {FIELDS} FROM Customer c WHERE c.MaKH=?", (parsed_id,)
        )
        if not customer:
            raise ApiError(404, "CUSTOMER_NOT_FOUND")
        tickets = database.fetch_all(
            "SELECT MaTicket id,TieuDe title,TrangThai status,MucDoUuTien priority,NgayTao createdAt "
            "FROM Ticket WHERE MaKH=? AND MaTicket<? ORDER BY MaTicket DESC LIMIT 51",
            (parsed_id, cursor),
        )
        chats = database.fetch_all(
            "SELECT MaSession id,TieuDe title,TrangThai status,ThoiGianBatDau createdAt FROM ChatSession "
            "WHERE MaKH=? ORDER BY MaSession DESC LIMIT 50",
            (parsed_id,),
        )
        return {
            "customer": customer,
            "tickets": tickets[:50],
            "chats": chats,
            "next": tickets[49]["id"] if len(tickets) > 50 else None,
        }

    @app.patch("/api/customers/{customer_id}")
    def update_contact(
        customer_id: str, payload: dict[str, Any], request: Request
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin", "Supervisor")
        parsed_id = numeric_id(customer_id)
        if payload.keys() - {"fullName", "email", "phone"}:
            raise ApiError(400, "INVALID_INPUT")
        values = _user_fields(payload, creating=False)
        customer = database.fetch_one(
            "SELECT MaUser FROM Customer WHERE MaKH=?", (parsed_id,)
        )
        if not customer:
            raise ApiError(404, "CUSTOMER_NOT_FOUND")
        try:
            with database.transaction() as tx:
                # Match account management lock order: account, then customer.
                if customer["MaUser"] is not None:
                    account = tx.fetch_one(
                        "SELECT MaUser FROM UserAccount WHERE MaUser=? FOR UPDATE",
                        (customer["MaUser"],),
                    )
                    if not account:
                        raise ApiError(409, "CUSTOMER_CHANGED")
                current = tx.fetch_one(
                    f"SELECT {FIELDS} FROM Customer c WHERE c.MaKH=? FOR UPDATE",
                    (parsed_id,),
                )
                if not current or current["userId"] != customer["MaUser"]:
                    raise ApiError(409, "CUSTOMER_CHANGED")
                name, email, phone = (
                    values.get(key, current[key]) for key in ("name", "email", "phone")
                )
                tx.execute(
                    "UPDATE Customer SET HoTen=?,Email=?,SoDienThoai=? WHERE MaKH=?",
                    (name, email, phone, parsed_id),
                )
                if current["userId"] is not None:
                    tx.execute(
                        "UPDATE UserAccount SET HoTen=?,Email=?,SoDienThoai=? WHERE MaUser=?",
                        (name, email, phone, current["userId"]),
                    )
                    tx.execute(
                        "DELETE FROM AuthOtpChallenge WHERE MaUser=?",
                        (current["userId"],),
                    )
                tx.execute(
                    "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong) VALUES(?,'CUSTOMER_UPDATE','Customer',?)",
                    (user["MaUser"], parsed_id),
                )
        except mysql.connector.errors.IntegrityError as error:
            if error.errno == 1062:
                raise ApiError(409, "EMAIL_EXISTS") from error
            raise
        return {"id": parsed_id}
