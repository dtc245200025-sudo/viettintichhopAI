import pytest

from backend.chats import _content, _id, _request_hash
from backend.errors import ApiError


def test_chat_request_hash_is_stable_for_unicode_payloads() -> None:
    expected = _request_hash("/api/chats", {"content": "Hỗ trợ 🙂"})

    assert expected == _request_hash("/api/chats", {"content": "Hỗ trợ 🙂"})
    assert expected != _request_hash("/api/chats", {"content": "Nội dung khác"})


def test_chat_message_validation_accepts_boundary_and_trims() -> None:
    assert _content("  Hỗ trợ 🙂  ") == "Hỗ trợ 🙂"
    assert len(_content("x" * 3000)) == 3000


@pytest.mark.parametrize("value", ["", "  ", "x" * 3001, 123])
def test_chat_message_validation_rejects_invalid_content(value: object) -> None:
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        _content(value)


@pytest.mark.parametrize("value", ["0", "-1", "abc", "2147483648"])
def test_chat_route_ids_reject_invalid_values(value: str) -> None:
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        _id(value)