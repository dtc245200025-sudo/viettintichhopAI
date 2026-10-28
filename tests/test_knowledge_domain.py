import json

import pytest

from backend.ai import AIProvider
from backend.config import Settings
from backend.errors import ApiError
from backend.knowledge import is_indexed, numeric_id, parse_vector, required_text


def test_index_state_requires_matching_content_model_and_dimensions() -> None:
    ai = AIProvider(Settings.from_env({"GEMINI_API_KEY": "test-key"}))
    content = "published instructions"
    rows = [{"content": content, "model": ai.model, "dimensions": ai.dimensions, "embedding": json.dumps([1.0] + [0.0] * (ai.dimensions - 1))}]

    assert is_indexed(rows, content, ai)
    assert not is_indexed(rows, content + " changed", ai)
    assert not is_indexed([{**rows[0], "model": "old-model"}], content, ai)


def test_parse_vector_and_knowledge_id_validation() -> None:
    assert parse_vector("[1,2]") == [1, 2]
    assert parse_vector("not-json") is None
    assert numeric_id("12") == 12
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        numeric_id("0")
    with pytest.raises(ApiError, match="INVALID_INPUT"):
        required_text("  ", 20)