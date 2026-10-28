import json
import pytest
from backend.ai import _unit_embedding, cosine, rank_chunks
from backend.errors import ApiError


def test_rank_matches_reference_cosine_and_stable_ties():
    vectors = [[3.0, 4.0, 0.0], [4.0, 3.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    rows = [{"id": i + 1, "embedding": json.dumps(v)} for i, v in enumerate(vectors)]
    result = rank_chunks(rows, [3.0, 4.0, 0.0], 0.1)
    expected = sorted(
        (r for r in rows if cosine([3.0, 4.0, 0.0], vectors[r["id"] - 1]) >= 0.1),
        key=lambda r: (-cosine([3.0, 4.0, 0.0], vectors[r["id"] - 1]), r["id"]),
    )[:3]
    assert [r["id"] for r in result] == [r["id"] for r in expected]
    assert [r["score"] for r in result] == pytest.approx(
        [cosine([3.0, 4.0, 0.0], vectors[r["id"] - 1]) for r in expected]
    )


def test_embedding_cache_tracks_value_changes_not_just_source_identifier():
    _unit_embedding.cache_clear()
    assert rank_chunks([{"id": 1, "embedding": "[1,0]"}], [1.0, 0.0], 0.5)
    assert not rank_chunks([{"id": 1, "embedding": "[0,1]"}], [1.0, 0.0], 0.5)
    assert _unit_embedding.cache_info().maxsize == 2048


@pytest.mark.parametrize("raw", ["invalid", "[true,0]", "[0,0]", "[1]", "[NaN,0]"])
def test_invalid_embeddings_never_become_sources(raw):
    assert rank_chunks([{"id": 1, "embedding": raw}], [1.0, 0.0], 0) == []


def test_invalid_query_vector_is_a_provider_error_not_an_answer():
    with pytest.raises(ApiError, match="AI_INVALID_OUTPUT"):
        rank_chunks([{"id": 1, "embedding": "[1,0]"}], [0.0, 0.0], 0.1)
