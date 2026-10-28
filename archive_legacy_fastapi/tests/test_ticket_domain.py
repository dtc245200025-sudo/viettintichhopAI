import pytest

from backend.errors import ApiError
from backend.tickets import PRIORITIES, STAGES, can_claim, evaluation_values, next_status, numeric_id, text_value


@pytest.mark.parametrize("current,target,expected", [
    (STAGES[0], STAGES[1], True),
    (STAGES[1], STAGES[2], True),
    (STAGES[2], STAGES[1], True),
    (STAGES[1], STAGES[3], True),
    (STAGES[2], STAGES[3], True),
    (STAGES[0], STAGES[2], False),
    (STAGES[3], STAGES[0], False),
])
def test_ticket_status_transition_follows_the_agreed_lifecycle(current: str, target: str, expected: bool) -> None:
    assert next_status(current, target) is expected


@pytest.mark.parametrize("agent_id,status,expected", [
    (None, STAGES[0], True),
    (7, STAGES[0], False),
    (None, STAGES[1], False),
    (None, STAGES[2], False),
])
def test_only_unassigned_new_tickets_can_be_claimed(agent_id: int | None, status: str, expected: bool) -> None:
    assert can_claim(agent_id, status) is expected


def test_assigned_agent_can_claim_their_new_ticket_but_others_cannot() -> None:
    assert can_claim(7, STAGES[0], 7)
    assert not can_claim(7, STAGES[0], 8)
    assert not can_claim(7, STAGES[1], 7)


def test_ticket_fields_match_the_source_document_limits() -> None:
    assert text_value(" title ", 200) == "title"
    assert text_value("x" * 2000, 2000) == "x" * 2000
    assert len(PRIORITIES) == 4
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        text_value("x" * 2001, 2000)


@pytest.mark.parametrize("payload", [
    {"stars": 0},
    {"stars": 6},
    {"stars": True},
    {"stars": "5"},
    {"stars": 5, "comment": "x" * 1001},
])
def test_csat_accepts_only_one_to_five_stars_and_bounded_comment(payload: dict[str, object]) -> None:
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        evaluation_values(payload)


def test_csat_comment_is_trimmed_and_optional() -> None:
    assert evaluation_values({"stars": 5, "comment": "  Helpful  "}) == (5, "Helpful")
    assert evaluation_values({"stars": 4}) == (4, None)


@pytest.mark.parametrize("value", ["0", "-1", "abc", "2147483648", "01"])
def test_ticket_ids_reject_malformed_or_overflow_values(value: str) -> None:
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        numeric_id(value)
