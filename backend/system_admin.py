import json
import re
from typing import Any

from fastapi import FastAPI, Request

from backend.ai import AIProvider
from backend.auth import _require_role, current_user
from backend.db import Database
from backend.errors import ApiError

SETTING_RULES = {
    "rag.threshold": ("decimal", 0.0, 1.0),
    "ai.timeout_seconds": ("integer", 5, 120),
    "auth.session_hours": ("integer", 1, 24),
}


def _apply(ai: AIProvider, key: str, value: str) -> None:
    if key == "rag.threshold":
        ai.retrieval_threshold = float(value)
    elif key == "ai.timeout_seconds":
        ai.timeout_seconds = int(value)


def _validated(key: object, value: object) -> tuple[str, str, str]:
    if not isinstance(key, str) or key not in SETTING_RULES or isinstance(value, bool):
        raise ApiError(400, "INVALID_INPUT")
    value_type, low, high = SETTING_RULES[key]
    try:
        if value_type == "integer" and (not str(value).isdecimal()):
            raise ValueError("integer required")
        number = int(value) if value_type == "integer" else float(value)
    except (TypeError, ValueError) as error:
        raise ApiError(400, "INVALID_INPUT") from error
    if not low <= number <= high:
        raise ApiError(400, "INVALID_INPUT")
    normalized = (
        str(number)
        if value_type == "integer"
        else f"{number:.2f}".rstrip("0").rstrip(".")
    )
    return key, normalized, value_type


def install_system_admin_routes(
    app: FastAPI, database: Database, ai: AIProvider
) -> None:
    try:
        for row in database.fetch_all(
            "SELECT SettingKey,SettingValue FROM SystemSetting"
        ):
            if row["SettingKey"] in SETTING_RULES:
                _apply(ai, row["SettingKey"], row["SettingValue"])
    except Exception:
        pass

    @app.get("/api/admin/settings")
    def list_settings(request: Request) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        rows = database.fetch_all(
            "SELECT s.SettingKey `key`,s.SettingValue value,s.ValueType type,s.UpdatedAt updatedAt,u.HoTen updatedBy "
            "FROM SystemSetting s LEFT JOIN UserAccount u ON u.MaUser=s.UpdatedBy ORDER BY s.SettingKey"
        )
        return {"settings": rows}

    @app.patch("/api/admin/settings/{setting_key}")
    def update_setting(
        setting_key: str, payload: dict[str, Any], request: Request
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        key, value, value_type = _validated(setting_key, payload.get("value"))
        with database.transaction() as transaction:
            current = transaction.fetch_one(
                "SELECT SettingValue FROM SystemSetting WHERE SettingKey=? FOR UPDATE",
                (key,),
            )
            if not current:
                raise ApiError(404, "SETTING_NOT_FOUND")
            transaction.execute(
                "UPDATE SystemSetting SET SettingValue=?,ValueType=?,UpdatedBy=?,UpdatedAt=UTC_TIMESTAMP(3) WHERE SettingKey=?",
                (value, value_type, user["MaUser"], key),
            )
            transaction.execute(
                "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,DiaChiIP,ChiTiet) VALUES(?,'SETTING_UPDATE','SystemSetting',?,?)",
                (
                    user["MaUser"],
                    request.client.host if request.client else None,
                    json.dumps(
                        {
                            "key": key,
                            "oldValue": current["SettingValue"],
                            "newValue": value,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        _apply(ai, key, value)
        return {"key": key, "value": value}

    @app.get("/api/admin/audit-logs")
    def audit_logs(
        request: Request,
        action: str | None = None,
        target: str | None = None,
        before: str | None = None,
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Admin")
        if action and (len(action) > 100 or not re.fullmatch(r"[A-Z0-9_]+", action)):
            raise ApiError(400, "INVALID_INPUT")
        if target and (len(target) > 100 or not re.fullmatch(r"[A-Za-z0-9_]+", target)):
            raise ApiError(400, "INVALID_INPUT")
        if before and (
            not before.isdecimal() or not 1 <= int(before) <= 9223372036854775807
        ):
            raise ApiError(400, "INVALID_INPUT")
        filters, values = [], []
        if action:
            filters.append("a.HanhDong=?")
            values.append(action)
        if target:
            filters.append("a.DoiTuong=?")
            values.append(target)
        if before:
            filters.append("a.MaLog<?")
            values.append(int(before))
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = database.fetch_all(
            "SELECT a.MaLog id,a.HanhDong action,a.DoiTuong target,a.MaDoiTuong targetId,a.DiaChiIP ip,a.ThoiGian createdAt,"
            "a.ChiTiet details,u.HoTen actorName,u.Email actorEmail FROM AuditLog a LEFT JOIN UserAccount u ON u.MaUser=a.MaUser "
            f"{where} ORDER BY a.MaLog DESC LIMIT 51",
            tuple(values),
        )
        logs = rows[:50]
        return {"logs": logs, "next": logs[-1]["id"] if len(rows) > 50 else None}
