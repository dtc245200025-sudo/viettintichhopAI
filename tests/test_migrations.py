from pathlib import Path

from backend.db import _sql
from backend.migrations import MIGRATION_FILES, ROOT, statements


def test_sql_statement_splitter_skips_comments_and_empty_statements() -> None:
    assert statements("-- comment\nSELECT 1;\n\n-- another\nSELECT 2;;") == [
        "SELECT 1",
        "SELECT 2",
    ]


def test_mysql_parameter_placeholders_are_converted_for_the_connector() -> None:
    assert (
        _sql("SELECT GET_LOCK(?,10) WHERE Version=?")
        == "SELECT GET_LOCK(%s,10) WHERE Version=%s"
    )


def test_python_runner_tracks_all_existing_migrations_and_ticket_assignment() -> None:
    counts = [
        len(statements((ROOT / "migrations" / filename).read_text(encoding="utf-8")))
        for filename in MIGRATION_FILES
    ]

    assert counts == [15, 1, 3, 3, 1, 1, 1, 3, 5, 7, 3]
    assert sum(counts) == 43
    assert Path(ROOT / "migrations" / "005_ticket_ai.sql").is_file()
    assert Path(ROOT / "migrations" / "006_auth_otp.sql").is_file()
    assert "CREATE TABLE AuthOtpChallenge" in (
        Path(ROOT) / "migrations" / "006_auth_otp.sql"
    ).read_text(encoding="utf-8")
    assert Path(ROOT / "migrations" / "007_ticket_assignment.sql").is_file()
    assert "CREATE TABLE TicketAssignmentHistory" in (
        Path(ROOT) / "migrations" / "007_ticket_assignment.sql"
    ).read_text(encoding="utf-8")
    assert Path(ROOT / "migrations" / "009_ticket_requirements.sql").is_file()
