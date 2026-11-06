from __future__ import annotations

from pathlib import Path

from probe.builder.graph import Graph
from probe.context.models import ContextCandidate, ContextRequest, ContextSnippet


class ContextAssembler:
    """Select source snippets for candidate nodes under a fixed token-like budget."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        try:
            return Path(path).read_text(encoding="utf-8").splitlines()
        except Exception:
            return []

    def _build_snippet(self, candidate: ContextCandidate, *, node_path: str | None = None) -> ContextSnippet | None:
        path = node_path or candidate.source_file
        if not path:
            return None

        lines = self._read_lines(path)
        if not lines:
            return ContextSnippet(
                entity_id=candidate.entity_id,
                path=path,
                start_line=1,
                end_line=1,
                text=f"# Source unavailable for {candidate.entity_id}",
                score=candidate.score,
                rationale=candidate.rationale,
            )

        span = candidate.source_span
        if span is not None:
            start_line, end_line = span
            start = max(1, start_line - 2)
            end = min(len(lines), end_line + 2)
        else:
            start = 1
            end = min(len(lines), 25)

        snippet_lines = lines[start - 1 : end]
        text = "\n".join(snippet_lines)
        return ContextSnippet(
            entity_id=candidate.entity_id,
            path=path,
            start_line=start,
            end_line=end,
            text=text,
            score=candidate.score,
            rationale=candidate.rationale,
        )

    def assemble(self, request: ContextRequest, candidates: list[ContextCandidate]) -> list[ContextSnippet]:
        request.validate()
        snippets: list[ContextSnippet] = []
        budget_used = 0
        for candidate in sorted(
            candidates,
            key=lambda item: (item.score if item.score is not None else 0.0, -item.graph_distance),
            reverse=True,
        )[: request.max_snippets]:
            path = candidate.source_file
            if self.graph is not None and not path:
                node = self.graph.get_node(candidate.entity_id)
                if node is not None:
                    path = node.file_path
                    candidate.source_file = path
                    if node.span is not None:
                        candidate.source_span = (node.span.start_line, node.span.end_line)
            snippet = self._build_snippet(candidate, node_path=path)
            if snippet is None:
                continue
            projected_budget = budget_used + len(snippet.text)
            if projected_budget > request.context_budget and snippets:
                break
            snippets.append(snippet)
            budget_used = projected_budget
            if len(snippets) >= request.max_snippets:
                break
        return snippets


def assemble_snippets(
    candidates: list[ContextCandidate],
    request: ContextRequest,
    *,
    graph: Graph | None = None,
) -> list[ContextSnippet]:
    return ContextAssembler(graph=graph).assemble(request, candidates)


__all__ = ["ContextAssembler", "assemble_snippets"]
