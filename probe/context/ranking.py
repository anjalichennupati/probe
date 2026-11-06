from __future__ import annotations

import json
from typing import Iterable

from probe.context.models import ContextCandidate, ContextRequest
from probe.llm.prompts import build_ranking_prompt
from probe.llm.schemas import RankingResult
from probe.providers.registry import build_provider


def _fallback_scores(candidates: Iterable[ContextCandidate]) -> list[ContextCandidate]:
    fallback: list[ContextCandidate] = []
    for candidate in candidates:
        distance = max(candidate.graph_distance, 1)
        score = max(0.0, 1.0 / (distance + 1.0))
        candidate.score = score
        candidate.rationale = candidate.rationale or "Structural fallback ranking"
        fallback.append(candidate)
    return fallback


def rank_candidates(
    candidates: Iterable[ContextCandidate],
    request: ContextRequest,
    *,
    objective: str | None = None,
) -> tuple[list[ContextCandidate], bool]:
    candidate_list = list(candidates)
    if not candidate_list:
        return [], False

    if not request.semantic_ranking:
        return _fallback_scores(candidate_list), True

    try:
        provider = build_provider()
    except Exception:
        return _fallback_scores(candidate_list), True

    allowed_ids = [candidate.entity_id for candidate in candidate_list]
    prompt_target = objective or request.target_id or ", ".join(request.changed_entity_ids)
    evidence = "\n".join(
        f"- {candidate.entity_id} ({candidate.entity_type}, distance={candidate.graph_distance}): {candidate.reason or 'discovered from graph'}"
        for candidate in candidate_list
    )
    prompt = build_ranking_prompt(
        target=prompt_target,
        candidates=[candidate.entity_id for candidate in candidate_list],
        evidence=evidence,
    )

    try:
        response = provider.complete([{"role": "user", "content": prompt}])
        payload = response.parsed
        if payload is None:
            text = response.text.strip()
            if text.startswith("{"):
                payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("provider response was not structured JSON")
        result = RankingResult.from_payload(payload, allowed_ids=allowed_ids)
    except Exception:
        return _fallback_scores(candidate_list), True

    by_id = {item.candidate_id: item for item in result.candidates}
    ranked: list[ContextCandidate] = []
    for candidate in candidate_list:
        ranked_item = by_id.get(candidate.entity_id)
        candidate.score = float(ranked_item.score) if ranked_item is not None else candidate.score
        candidate.rationale = ranked_item.rationale if ranked_item is not None else candidate.rationale
        if candidate.score is None:
            candidate.score = 0.0
        ranked.append(candidate)

    ranked.sort(key=lambda item: (item.score if item.score is not None else 0.0, -item.graph_distance), reverse=True)
    return ranked, False


__all__ = ["rank_candidates"]
