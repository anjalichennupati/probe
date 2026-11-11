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
    source: ContextSource = field(default_factory=lambda: ContextSource())
    score: float | None = None
    rationale: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def source_file(self) -> str | None:
        return self.source.file

    @source_file.setter
    def source_file(self, value: str | None) -> None:
        self.source.file = value

    @property
    def source_span(self) -> tuple[int, int] | None:
        if self.source.span is None:
            return None
        return self.source.span[0], self.source.span[1]

    @source_span.setter
    def source_span(self, value: tuple[int, int] | None) -> None:
        self.source.span = list(value) if value is not None else None


@dataclass
class ContextSource:
    """Source location attached to a retrieved graph entity."""

    file: str | None = None
    span: list[int] | None = None


@dataclass
class ContextSnippet:
    """Source snippet selected for retrieval."""

    entity_id: str
    path: str
    lines: ContextLines
    text: str
    score: float | None = None
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def start_line(self) -> int:
        return self.lines.start

    @property
    def end_line(self) -> int:
        return self.lines.end


@dataclass
class ContextLines:
    """Inclusive line range represented by a snippet."""

    start: int
    end: int


@dataclass
class ContextSummary:
    """Computed counts and budget usage for a context response."""

    fallback_used: bool
    budget_used: int
    candidate_count: int
    snippet_count: int
    omission_count: int
    unresolved_count: int
    error_count: int


@dataclass
class ContextRequestOutput:
    """Public request portion of a context response."""

    mode: Literal["target", "change"]
    target_id: str | None
    changed_entity_ids: list[str]
    depth: int
    max_candidates: int
    max_snippets: int
    context_budget: int
    semantic_ranking: bool
    provider_name: str | None


@dataclass
class ContextResponse:
    """Typed, nested response contract returned by context retrieval."""

    schema_version: int
    status: str
    request: ContextRequestOutput
    summary: ContextSummary
    candidates: list[ContextCandidate]
    snippets: list[ContextSnippet]
    omissions: list[str]
    unresolved: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), **kwargs)


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

    @property
    def summary(self) -> ContextSummary:
        return ContextSummary(
            fallback_used=self.fallback_used,
            budget_used=self.budget_used,
            candidate_count=len(self.candidates),
            snippet_count=len(self.snippets),
            omission_count=len(self.omissions),
            unresolved_count=len(self.unresolved),
            error_count=len(self.errors),
        )

    def to_response(self) -> ContextResponse:
        request = self.request
        return ContextResponse(
            schema_version=1,
            status=self.completion,
            request=ContextRequestOutput(
                mode=request.retrieval_mode,
                target_id=request.target_id,
                changed_entity_ids=request.changed_entity_ids,
                depth=request.depth,
                max_candidates=request.max_candidates,
                max_snippets=request.max_snippets,
                context_budget=request.context_budget,
                semantic_ranking=request.semantic_ranking,
                provider_name=request.provider_name,
            ),
            summary=self.summary,
            candidates=self.candidates,
            snippets=self.snippets,
            omissions=self.omissions,
            unresolved=self.unresolved,
            errors=self.errors,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_response().to_dict()

    def to_json(self, **kwargs: Any) -> str:
        return self.to_response().to_json(**kwargs)


__all__ = [
    "ContextCandidate",
    "ContextLines",
    "ContextPackage",
    "ContextRequest",
    "ContextRequestOutput",
    "ContextResponse",
    "ContextSource",
    "ContextSnippet",
    "ContextSummary",
]
