from __future__ import annotations

from probe.builder.graph import Graph
from probe.context.assembler import ContextAssembler
from probe.context.models import ContextCandidate, ContextPackage, ContextRequest
from probe.context.ranking import rank_candidates
from probe.context.traversal import discover_candidates, resolve_entity_ids


class ContextEngine:
    """Orchestrates graph traversal, ranking, and snippet assembly for retrieval requests."""

    def __init__(self, graph: Graph, *, assembler: ContextAssembler | None = None) -> None:
        self.graph = graph
        self.assembler = assembler or ContextAssembler(graph)

    def run(self, request: ContextRequest) -> ContextPackage:
        request.validate()

        if request.retrieval_mode == "target":
            seed_ids = [request.target_id]
        else:
            seed_ids = list(request.changed_entity_ids)

        resolved_ids, unresolved = resolve_entity_ids(self.graph, seed_ids)
        if not resolved_ids:
            return ContextPackage(
                request=request,
                candidates=[],
                snippets=[],
                unresolved=unresolved,
                errors=["No matching graph entities were found for the request."],
                completion="partial",
            )

        discovered = discover_candidates(
            self.graph,
            resolved_ids,
            depth=request.depth,
            max_candidates=request.max_candidates,
        )

        if request.retrieval_mode == "target" and request.target_id:
            target_node = self.graph.get_node(request.target_id)
            if target_node is not None:
                target_candidate = ContextCandidate(
                    entity_id=target_node.id,
                    entity_type=target_node.type.value,
                    graph_distance=0,
                    discovery_paths=[f"seed:{target_node.id}"],
                    source_file=target_node.file_path,
                    source_span=(
                        (target_node.span.start_line, target_node.span.end_line)
                        if target_node.span is not None
                        else None
                    ),
                    reason="target entity",
                    metadata={"entity_type": target_node.type.value},
                )
                discovered = [target_candidate] + [item for item in discovered if item.entity_id != target_node.id]

        ranked_candidates, fallback_used = rank_candidates(discovered, request)
        ordered_candidates = sorted(
            ranked_candidates,
            key=lambda item: (item.score if item.score is not None else 0.0, -item.graph_distance),
            reverse=True,
        )[: request.max_candidates]

        snippets = self.assembler.assemble(request, ordered_candidates)
        omissions = [candidate.entity_id for candidate in ordered_candidates if candidate.entity_id not in {snippet.entity_id for snippet in snippets}]

        return ContextPackage(
            request=request,
            candidates=ordered_candidates,
            snippets=snippets,
            omissions=omissions,
            unresolved=unresolved,
            fallback_used=fallback_used,
            budget_used=sum(len(snippet.text) for snippet in snippets),
            completion="complete" if len(snippets) == len(ordered_candidates) and not omissions else "partial",
        )

    def retrieve(self, request: ContextRequest) -> ContextPackage:
        return self.run(request)


__all__ = ["ContextEngine"]
