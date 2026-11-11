from probe.context.models import ContextCandidate, ContextRequest
from probe.context.ranking import rank_candidates
from probe.providers.base import ProviderResponse


def test_rank_candidates_requests_json_and_validates_response(monkeypatch):
    expected_payload = {
        "candidates": [
            {"candidate_id": "candidate-1", "score": 0.9, "rationale": "Directly relevant."}
        ]
    }
    calls = {}

    class FakeProvider:
        def structured(self, messages, schema, **kwargs):
            calls["messages"] = messages
            calls["schema"] = schema
            calls["kwargs"] = kwargs
            return ProviderResponse(text="", parsed=expected_payload)

    monkeypatch.setattr("probe.context.ranking.build_provider", lambda: FakeProvider())
    candidate = ContextCandidate(entity_id="candidate-1", entity_type="function")
    request = ContextRequest(
        retrieval_mode="target",
        target_id="target-1",
        semantic_ranking=True,
    )

    ranked, fallback_used = rank_candidates([candidate], request)

    assert fallback_used is False
    assert ranked[0].score == 0.9
    assert calls["kwargs"]["name"] == "candidate_rankings"
    schema = calls["schema"]
    assert schema["properties"]["candidates"]["items"]["properties"]["candidate_id"]["enum"] == [
        "candidate-1"
    ]
