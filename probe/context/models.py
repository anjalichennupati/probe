from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class ContextRequest:
    """Retrieval request for the Probe context engine."""

    retrieval_mode: Literal["target", "change"]
    target_id: str | None = None
    changed_entity_ids: list[str] = field(default_factory=list)
    depth: int = 2
    max_candidates: int = 25
    max_snippets: int = 8
    context_budget: int = 12000
    semantic_ranking: bool = True
    provider_name: str | None = None

    def validate(self) -> None:
        if self.depth < 0:
            raise ValueError("depth must be >= 0")
        if self.max_candidates <= 0:
            raise ValueError("max_candidates must be > 0")
        if self.max_snippets <= 0:
            raise ValueError("max_snippets must be > 0")
        if self.context_budget <= 0:
            raise ValueError("context_budget must be > 0")
        if self.retrieval_mode == "target" and not self.target_id:
            raise ValueError("target_id is required for target retrieval")
        if self.retrieval_mode == "change" and not self.changed_entity_ids:
            raise ValueError("changed_entity_ids is required for change retrieval")


@dataclass
class ContextCandidate:
    """A candidate entity discovered from the graph and optionally ranked."""

    entity_id: str
    entity_type: str
    graph_distance: int = 0
    discovery_paths: list[str] = field(default_factory=list)
    source_file: str | None = None
    source_span: tuple[int, int] | None = None
    score: float | None = None
    rationale: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "graph_distance": self.graph_distance,
            "score": self.score,
            "rationale": self.rationale,
            "reason": self.reason,
            "discovery_paths": self.discovery_paths,
            "source": {
                "file": self.source_file,
                "span": list(self.source_span) if self.source_span is not None else None,
            },
            "metadata": self.metadata,
        }


@dataclass
class ContextSnippet:
    """Source snippet selected for retrieval."""

    entity_id: str
    path: str
    start_line: int
    end_line: int
    text: str
    score: float | None = None
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "path": self.path,
            "lines": {"start": self.start_line, "end": self.end_line},
            "text": self.text,
            "score": self.score,
            "rationale": self.rationale,
        }


@dataclass
class ContextPackage:
    """Final context package returned by the engine."""

    request: ContextRequest
    candidates: list[ContextCandidate] = field(default_factory=list)
    snippets: list[ContextSnippet] = field(default_factory=list)
    omissions: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fallback_used: bool = False
    budget_used: int = 0
    completion: str = "partial"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.completion,
            "request": {
                "mode": self.request.retrieval_mode,
                "target_id": self.request.target_id,
                "changed_entity_ids": self.request.changed_entity_ids,
                "depth": self.request.depth,
                "max_candidates": self.request.max_candidates,
                "max_snippets": self.request.max_snippets,
                "context_budget": self.request.context_budget,
                "semantic_ranking": self.request.semantic_ranking,
                "provider_name": self.request.provider_name,
            },
            "summary": {
                "fallback_used": self.fallback_used,
                "budget_used": self.budget_used,
                "candidate_count": len(self.candidates),
                "snippet_count": len(self.snippets),
                "omission_count": len(self.omissions),
                "unresolved_count": len(self.unresolved),
                "error_count": len(self.errors),
            },
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "snippets": [snippet.to_dict() for snippet in self.snippets],
            "omissions": self.omissions,
            "unresolved": self.unresolved,
            "errors": self.errors,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), **kwargs)


__all__ = [
    "ContextCandidate",
    "ContextPackage",
    "ContextRequest",
    "ContextSnippet",
]
