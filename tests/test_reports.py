from datetime import date, timedelta

import pytest

from backend.errors import ApiError
from backend.reports import SLA_HOURS, report_period


def test_report_period_defaults_to_a_30_day_window() -> None:
    start, end = report_period(None, None)

    assert end - start == timedelta(days=29)


def test_report_period_accepts_explicit_iso_dates() -> None:
    assert report_period("2026-09-01", "2026-09-27") == (date(2026, 9, 1), date(2026, 9, 27))


def test_demo_sla_policy_is_stricter_for_higher_priority_tickets() -> None:
    assert SLA_HOURS == {"Khẩn cấp": 4, "Cao": 8, "Trung bình": 24, "Thấp": 48}


@pytest.mark.parametrize("start,end", [
    ("2026-09-28", "2026-09-27"),
    ("2024-01-01", "2026-09-27"),
    ("2026-02-30", "2026-03-01"),
    ("today", "2026-09-27"),
])
def test_report_period_rejects_invalid_or_excessive_ranges(start: str, end: str) -> None:
    with pytest.raises(ApiError):
        report_period(start, end)
