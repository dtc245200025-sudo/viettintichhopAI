from datetime import date, datetime, timedelta, timezone
import re
from typing import Any

from fastapi import FastAPI, Request

from backend.auth import _require_role, current_user
from backend.db import Database
from backend.errors import ApiError

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLA_HOURS = {"Khẩn cấp": 4, "Cao": 8, "Trung bình": 24, "Thấp": 48}


def report_period(start: str | None, end: str | None) -> tuple[date, date]:
    end_date = _parse_date(end) if end else datetime.now(timezone.utc).date()
    start_date = _parse_date(start) if start else end_date - timedelta(days=29)
    if start_date > end_date or (end_date - start_date).days > 365:
        raise ApiError(400, "INVALID_DATE_RANGE")
    return start_date, end_date


def _parse_date(value: str) -> date:
    if not DATE_PATTERN.fullmatch(value):
        raise ApiError(400, "INVALID_INPUT")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(400, "INVALID_INPUT") from error


def install_report_routes(app: FastAPI, database: Database) -> None:
    @app.get("/api/reports/summary")
    def report_summary(
        request: Request, startDate: str | None = None, endDate: str | None = None
    ) -> dict[str, Any]:
        user = current_user(request, database)
        _require_role(user, "Supervisor")
        start_date, end_date = report_period(startDate, endDate)
        parameters = (start_date, end_date)
        tickets_by_status = database.fetch_all(
            "SELECT TrangThai status,COUNT(*) count FROM Ticket "
            "WHERE NgayTao>=? AND NgayTao<DATE_ADD(?,INTERVAL 1 DAY) GROUP BY TrangThai ORDER BY TrangThai",
            parameters,
        )
        tickets_by_category = database.fetch_all(
            "SELECT COALESCE(c.TenCategory,'Chưa phân loại') category,COUNT(*) count FROM Ticket t "
            "LEFT JOIN TicketCategory c ON c.MaCategory=t.MaCategory "
            "WHERE t.NgayTao>=? AND t.NgayTao<DATE_ADD(?,INTERVAL 1 DAY) "
            "GROUP BY c.MaCategory,c.TenCategory ORDER BY count DESC,category LIMIT 10",
            parameters,
        )
        tickets_by_priority = database.fetch_all(
            "SELECT MucDoUuTien priority,COUNT(*) count FROM Ticket "
            "WHERE NgayTao>=? AND NgayTao<DATE_ADD(?,INTERVAL 1 DAY) GROUP BY MucDoUuTien ORDER BY MucDoUuTien",
            parameters,
        )
        resolution = database.fetch_one(
            "SELECT COUNT(*) closedTickets,AVG(TIMESTAMPDIFF(MINUTE,NgayTao,NgayDong)) averageMinutes "
            "FROM Ticket WHERE NgayDong IS NOT NULL AND NgayTao>=? AND NgayTao<DATE_ADD(?,INTERVAL 1 DAY)",
            parameters,
        ) or {"closedTickets": 0, "averageMinutes": None}
        sla = database.fetch_one(
            "SELECT COUNT(*) totalTickets,SUM(TIMESTAMPDIFF(MINUTE,NgayTao,COALESCE(NgayDong,UTC_TIMESTAMP(3)))>"
            "CASE MucDoUuTien WHEN 'Khẩn cấp' THEN 240 WHEN 'Cao' THEN 480 WHEN 'Thấp' THEN 2880 ELSE 1440 END) overdueTickets "
            "FROM Ticket WHERE NgayTao>=? AND NgayTao<DATE_ADD(?,INTERVAL 1 DAY)",
            parameters,
        ) or {"totalTickets": 0, "overdueTickets": 0}
        sessions = database.fetch_one(
            "SELECT COUNT(*) count FROM ChatSession WHERE ThoiGianBatDau>=? AND ThoiGianBatDau<DATE_ADD(?,INTERVAL 1 DAY)",
            parameters,
        )
        ratings = database.fetch_one(
            "SELECT COUNT(*) total,AVG(SoSao) averageStars,SUM(SoSao>=4) satisfied "
            "FROM Evaluation WHERE NgayDanhGia>=? AND NgayDanhGia<DATE_ADD(?,INTERVAL 1 DAY)",
            parameters,
        ) or {"total": 0, "averageStars": None, "satisfied": 0}
        total_ratings = int(ratings["total"] or 0)
        satisfied = int(ratings["satisfied"] or 0)
        return {
            "period": {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
            },
            "ticketsByStatus": tickets_by_status,
            "ticketsByCategory": tickets_by_category,
            "ticketsByPriority": tickets_by_priority,
            "resolution": resolution,
            "sla": {
                "overdueTickets": int(sla["overdueTickets"] or 0),
                "policyHours": SLA_HOURS,
            },
            "chatSessions": int(sessions["count"] if sessions else 0),
            "csat": {
                "total": total_ratings,
                "averageStars": ratings["averageStars"],
                "satisfiedCount": satisfied,
                "satisfactionPercent": (
                    round(satisfied * 100 / total_ratings, 1) if total_ratings else None
                ),
            },
        }
