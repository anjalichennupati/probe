from __future__ import annotations

from collections import deque
from typing import Iterable

from probe.builder.graph import Graph
from probe.model.models import Node
from probe.context.models import ContextCandidate


def resolve_entity_ids(graph: Graph, identifiers: Iterable[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    unresolved: list[str] = []
    for identifier in identifiers:
        if not identifier:
            continue
        node = graph.get_node(identifier)
        if node is not None:
            resolved.append(node.id)
            continue
        matched = None
        for candidate in graph.get_nodes():
            if candidate.name == identifier or candidate.detailed_name == identifier:
                matched = candidate.id
                break
        if matched is not None:
            resolved.append(matched)
        else:
            unresolved.append(identifier)
    return resolved, unresolved


def discover_candidates(
    graph: Graph,
    seed_ids: Iterable[str],
    *,
    depth: int = 2,
    max_candidates: int = 25,
) -> list[ContextCandidate]:
    seed_list = list(seed_ids)
    if not seed_list:
        return []

    discovered: dict[str, ContextCandidate] = {}
    queue: deque[tuple[str, int, str]] = deque()
    seen: dict[str, int] = {}

    for seed in seed_list:
        if graph.get_node(seed) is None:
            continue
        queue.append((seed, 0, f"seed:{seed}"))
        seen[seed] = 0

    while queue:
        node_id, distance, path = queue.popleft()
        if distance >= depth:
            continue
        node = graph.get_node(node_id)
        if node is None:
            continue
        for edge in graph.get_outgoing(node_id):
            if edge.target_id is None:
                continue
            next_distance = distance + 1
            if next_distance > depth:
                continue
            next_node = graph.get_node(edge.target_id)
            if next_node is None:
                continue
            candidate = discovered.get(edge.target_id)
            if candidate is None or next_distance < candidate.graph_distance:
                candidate = ContextCandidate(
                    entity_id=edge.target_id,
                    entity_type=next_node.type.value,
                    graph_distance=next_distance,
                    discovery_paths=[f"{node_id}:{edge.type.value}:{edge.target_id}"],
                    source_file=next_node.file_path,
                    source_span=(
                        (next_node.span.start_line, next_node.span.end_line)
                        if next_node.span is not None
                        else None
                    ),
                    reason=f"reachable via {edge.type.value}",
                    metadata={"edge_type": edge.type.value},
                )
                discovered[edge.target_id] = candidate
            else:
                path_label = f"{node_id}:{edge.type.value}:{edge.target_id}"
                if path_label not in candidate.discovery_paths:
                    candidate.discovery_paths.append(path_label)
                candidate.reason = candidate.reason or f"reachable via {edge.type.value}"
            if edge.target_id not in seen or next_distance < seen[edge.target_id]:
                seen[edge.target_id] = next_distance
                queue.append((edge.target_id, next_distance, path))

        for edge in graph.get_incoming(node_id):
            if edge.source_id is None:
                continue
            next_distance = distance + 1
            if next_distance > depth:
                continue
            source_node = graph.get_node(edge.source_id)
            if source_node is None:
                continue
            candidate = discovered.get(edge.source_id)
            if candidate is None or next_distance < candidate.graph_distance:
                candidate = ContextCandidate(
                    entity_id=edge.source_id,
                    entity_type=source_node.type.value,
                    graph_distance=next_distance,
                    discovery_paths=[f"{edge.source_id}:{edge.type.value}:{node_id}"],
                    source_file=source_node.file_path,
                    source_span=(
                        (source_node.span.start_line, source_node.span.end_line)
                        if source_node.span is not None
                        else None
                    ),
                    reason=f"reachable via {edge.type.value} from {node_id}",
                    metadata={"edge_type": edge.type.value},
                )
                discovered[edge.source_id] = candidate
            else:
                path_label = f"{edge.source_id}:{edge.type.value}:{node_id}"
                if path_label not in candidate.discovery_paths:
                    candidate.discovery_paths.append(path_label)
            if edge.source_id not in seen or next_distance < seen[edge.source_id]:
                seen[edge.source_id] = next_distance
                queue.append((edge.source_id, next_distance, path))

    ordered = sorted(
        discovered.values(),
        key=lambda item: (item.graph_distance, item.entity_id),
    )
    return ordered[:max_candidates]


__all__ = ["discover_candidates", "resolve_entity_ids"]
