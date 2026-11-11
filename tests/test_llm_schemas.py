import pytest

from probe.llm.schemas import RankingResult


def test_ranking_result_validates_candidate_ids_and_scores():
    payload = {
        "candidates": [
            {"candidate_id": "a", "score": 0.95, "rationale": "Direct dependency"},
            {"candidate_id": "b", "score": 0.4, "rationale": "Semantic match"},
        ]
    }

    result = RankingResult.from_payload(payload, allowed_ids=["a", "b"])

    assert [candidate.candidate_id for candidate in result.candidates] == ["a", "b"]
    assert result.missing_candidates == []


def test_ranking_result_builds_provider_schema_from_model_fields():
    schema = RankingResult.json_schema(allowed_ids=["a", "b"])

    assert schema["required"] == ["candidates"]
    candidate_schema = schema["properties"]["candidates"]["items"]
    assert candidate_schema["required"] == ["candidate_id", "score", "rationale"]
    assert candidate_schema["properties"]["candidate_id"]["enum"] == ["a", "b"]
    assert candidate_schema["properties"]["score"]["minimum"] == 0
    assert candidate_schema["properties"]["score"]["maximum"] == 1


def test_ranking_result_rejects_duplicate_or_unknown_candidates():
    payload = {
        "candidates": [
            {"candidate_id": "a", "score": 0.8, "rationale": "first"},
            {"candidate_id": "a", "score": 0.7, "rationale": "duplicate"},
        ]
    }

    with pytest.raises(ValueError, match="duplicate|Duplicate"):
        RankingResult.from_payload(payload, allowed_ids=["a", "b"])

    payload = {"candidates": [{"candidate_id": "x", "score": 0.5, "rationale": "unknown"}]}
    with pytest.raises(ValueError, match="Unknown|unknown"):
        RankingResult.from_payload(payload, allowed_ids=["a", "b"])


def test_ranking_result_requires_missing_candidates_to_be_explicit():
    payload = {"candidates": [{"candidate_id": "a", "score": 0.9, "rationale": "only one"}]}

    with pytest.raises(ValueError, match="missing"):
        RankingResult.from_payload(payload, allowed_ids=["a", "b"])
