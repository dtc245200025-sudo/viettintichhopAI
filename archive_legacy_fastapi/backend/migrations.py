import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import mysql.connector

from backend.config import Settings
from backend.db import _sql


ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILES = (
    "001_auth_and_support.sql",
    "002_ticket_requests.sql",
    "003_chat_history.sql",
    "004_knowledge_rag.sql",
    "005_ticket_ai.sql",
    "006_auth_otp.sql",
    "007_ticket_assignment.sql",
    "008_handover_summary_admin.sql",
    "009_ticket_requirements.sql",
)


def statements(source: str) -> list[str]:
    without_comments = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("--"))
    return [statement.strip() for statement in without_comments.split(";") if statement.strip()]


def _rows(connection: Any, sql: str, values: tuple[object, ...] = ()) -> list[dict[str, Any]]:
    cursor = connection.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(_sql(sql), values)
        return cursor.fetchall()
    finally:
        cursor.close()


def _execute(connection: Any, sql: str, values: tuple[object, ...] = ()) -> int:
    cursor = connection.cursor()
    try:
        cursor.execute(_sql(sql), values)
        return int(cursor.lastrowid)
    finally:
        cursor.close()


def preflight(connection: Any) -> None:
    checks = [
        ("duplicate-email", "SELECT COUNT(*) n FROM (SELECT LOWER(TRIM(Email)) FROM UserAccount WHERE Email IS NOT NULL GROUP BY LOWER(TRIM(Email)) HAVING COUNT(*)>1) d"),
        ("invalid-email", "SELECT COUNT(*) n FROM UserAccount WHERE Email IS NOT NULL AND (TRIM(Email)='' OR TRIM(Email) NOT LIKE '%_@_%._%')"),
        ("ticket-owner", "SELECT COUNT(*) n FROM Ticket t JOIN ChatSession s ON t.MaSession=s.MaSession WHERE t.MaKH<>s.MaKH"),
        ("ticket-status", "SELECT COUNT(*) n FROM Ticket WHERE TrangThai IS NULL OR TrangThai NOT IN ('Mới','Đang xử lý','Đã giải quyết','Chờ khách hàng','Đã đóng') OR MucDoUuTien IS NULL OR MucDoUuTien NOT IN ('Thấp','Trung bình','Cao','Khẩn cấp')"),
        ("evaluation-target", "SELECT COUNT(*) n FROM Evaluation WHERE (MaSession IS NOT NULL)+(MaTicket IS NOT NULL)<>1 OR SoSao IS NULL OR SoSao NOT BETWEEN 1 AND 5 OR DiemNPS NOT BETWEEN 0 AND 10"),
        ("evaluation-owner", "SELECT COUNT(*) n FROM Evaluation e LEFT JOIN Ticket t ON e.MaTicket=t.MaTicket LEFT JOIN ChatSession s ON e.MaSession=s.MaSession WHERE (t.MaKH IS NOT NULL AND t.MaKH<>e.MaKH) OR (s.MaKH IS NOT NULL AND s.MaKH<>e.MaKH)"),
        ("duplicate-rating-session", "SELECT COUNT(*) n FROM (SELECT MaSession FROM Evaluation WHERE MaSession IS NOT NULL GROUP BY MaSession HAVING COUNT(*)>1) d"),
        ("duplicate-rating-ticket", "SELECT COUNT(*) n FROM (SELECT MaTicket FROM Evaluation WHERE MaTicket IS NOT NULL GROUP BY MaTicket HAVING COUNT(*)>1) d"),
        ("sentiment-label", "SELECT COUNT(*) n FROM SentimentAnalysis WHERE CamXuc NOT IN ('Tích cực','Trung tính','Tiêu cực')"),
        ("handover-status", "SELECT COUNT(*) n FROM Handover WHERE TrangThai IS NULL OR TrangThai NOT IN ('Chờ tiếp nhận','Đã tiếp nhận','Đã kết thúc','Đã hủy')"),
        ("handover-duplicate", "SELECT COUNT(*) n FROM (SELECT MaSession FROM Handover WHERE TrangThai IN ('Chờ tiếp nhận','Đã tiếp nhận') GROUP BY MaSession HAVING COUNT(*)>1) d"),
        ("ticket-time", "SELECT COUNT(*) n FROM Ticket WHERE NgayTao IS NULL OR NgayCapNhat<NgayTao OR (NgayDong IS NOT NULL AND (NgayDong<NgayTao OR TrangThai<>'Đã đóng'))"),
        ("chat-time", "SELECT COUNT(*) n FROM ChatSession WHERE ThoiGianKetThuc IS NOT NULL AND (ThoiGianBatDau IS NULL OR ThoiGianKetThuc<ThoiGianBatDau)"),
        ("confidence-range", "SELECT COUNT(*) n FROM Message WHERE DoTinCayAI NOT BETWEEN 0 AND 100"),
    ]
    issues = []
    for name, sql in checks:
        count = _rows(connection, sql)[0]["n"]
        if int(count):
            issues.append(f"{name}: {count}")
    if issues:
        raise RuntimeError("Preflight failed; no application schema changed. Resolve records explicitly: " + ", ".join(issues))


def migrate(settings: Settings, *, initialize: bool = False, check: bool = False) -> dict[str, Any]:
    options = dict(settings.database)
    database_name = str(options.pop("database"))
    connection = mysql.connector.connect(**options)
    lock_acquired = False
    lock_name = f"vietincare:{database_name}"
    try:
        _execute(connection, "SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        _execute(connection, "SET SESSION time_zone='+00:00'")
        version = _rows(connection, "SELECT VERSION() version")[0]["version"]
        if not str(version).startswith("8.0.46"):
            raise RuntimeError("This project requires MySQL Community Server 8.0.46")
        if int(_rows(connection, "SELECT GET_LOCK(?,10) acquired", (lock_name,))[0]["acquired"] or 0) != 1:
            raise RuntimeError("Migration lock unavailable")
        lock_acquired = True
        if initialize:
            _execute(connection, f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        _execute(connection, f"USE `{database_name}`")
        tables = {row["TABLE_NAME"].casefold() for row in _rows(connection, "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=?", (database_name,))}
        if initialize:
            if tables:
                raise RuntimeError("--init requires an empty database; use migrations on an existing schema")
            initial_sql = (ROOT / "SQLQuery1.sql").read_text(encoding="utf-8")
            for statement in statements(initial_sql):
                if re.match(r"^CREATE TABLE", statement, re.IGNORECASE):
                    _execute(connection, statement)
        if "schemamigration" in tables:
            recorded = _rows(connection, "SELECT Version,Step,Checksum,State FROM SchemaMigration ORDER BY Version,Step")
        else:
            recorded = []
        if any(row["Version"] < 1 or row["Version"] > len(MIGRATION_FILES) for row in recorded):
            raise RuntimeError("Unknown migration version; no automatic changes")

        plans = []
        previous_pending = False
        for version_number, filename in enumerate(MIGRATION_FILES, start=1):
            source = (ROOT / "migrations" / filename).read_text(encoding="utf-8")
            checksum = hashlib.sha256(source.encode("utf-8")).hexdigest()
            steps = statements(source)
            version_rows = [row for row in recorded if row["Version"] == version_number]
            valid = all(
                row["Step"] == index and row["Checksum"] == checksum and row["State"] == "done"
                for index, row in enumerate(version_rows, start=1)
            )
            if len(version_rows) > len(steps) or not valid:
                raise RuntimeError("Migration has changed or a step was interrupted. Inspect SchemaMigration and actual DDL; see migrations/README.md. No automatic retry.")
            remaining = len(steps) - len(version_rows)
            if version_rows and previous_pending:
                raise RuntimeError("Migration versions are out of order; inspect SchemaMigration")
            previous_pending = previous_pending or remaining > 0
            plans.append({"version": version_number, "checksum": checksum, "steps": steps, "remaining": remaining})

        remaining_total = sum(plan["remaining"] for plan in plans)
        total_steps = sum(len(plan["steps"]) for plan in plans)
        if remaining_total == 0:
            return {"status": "current", "steps": total_steps}
        if plans[0]["remaining"]:
            preflight(connection)
        if check:
            return {"status": "ready", "remaining": remaining_total}
        if "schemamigration" not in tables:
            _execute(
                connection,
                "CREATE TABLE SchemaMigration (Version INT NOT NULL, Step INT NOT NULL, Checksum CHAR(64) NOT NULL, "
                "State VARCHAR(10) NOT NULL, AppliedAt DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), "
                "PRIMARY KEY(Version,Step)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            )
        for plan in plans:
            start_at = len(plan["steps"]) - plan["remaining"]
            for index in range(start_at, len(plan["steps"])):
                step = index + 1
                _execute(connection, "INSERT INTO SchemaMigration(Version,Step,Checksum,State) VALUES(?,?,?,'running')", (plan["version"], step, plan["checksum"]))
                connection.commit()
                _execute(connection, plan["steps"][index])
                _execute(connection, "UPDATE SchemaMigration SET State='done',AppliedAt=UTC_TIMESTAMP(3) WHERE Version=? AND Step=?", (plan["version"], step))
                connection.commit()
        return {"status": "applied", "steps": total_steps}
    finally:
        if lock_acquired:
            try:
                _rows(connection, "SELECT RELEASE_LOCK(?) released", (lock_name,))
            except mysql.connector.Error:
                pass
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--init", action="store_true")
    args = parser.parse_args()
    try:
        result = migrate(Settings.from_env(), initialize=args.init, check=args.check)
        print(json.dumps(result))
    except Exception as error:
        print(getattr(error, "code", None) or str(error))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
