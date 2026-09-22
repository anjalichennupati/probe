from typing import Any

from probe.builder import Graph
from probe.model.models import Edge


def _node_dict(node: Any, node_hash: str | None = None) -> dict[str, Any]:
    span = node.span
    return {
        "id": node.id,
        "name": node.name,
        "kind": node.type.value,
        "qualified_name": node.detailed_name,
        "file": node.file_path,
        "location": {
            "start_line": span.start_line,
            "start_column": span.start_column,
            "end_line": span.end_line,
            "end_column": span.end_column,
        }
        if span
        else None,
        "parent_id": node.parent_id,
        "docstring": node.docstring,
        "metadata": node.metadata,
        "hash": node_hash,
    }


def _edge_dict(edge: Edge) -> dict[str, Any]:
    return {
        "source": edge.source_id,
        "target": edge.target_id,
        "target_ref": edge.target_ref,
        "type": edge.type.value,
        "metadata": edge.metadata,
    }


def node_payload(graph: Graph, node_id: str) -> dict[str, Any] | None:
    node = graph.get_node(node_id)
    if node is None:
        return None
    return {
        "node": _node_dict(node, graph.get_node_hashes().get(node_id)),
        "incoming": [_edge_dict(edge) for edge in graph.get_incoming(node_id)],
        "outgoing": [_edge_dict(edge) for edge in graph.get_outgoing(node_id)],
    }


def graph_payload(graph: Graph, max_nodes: int | None = None) -> dict[str, Any]:
    nodes = graph.get_nodes()
    if max_nodes is not None:
        nodes = nodes[:max_nodes]
    visible_ids = {node.id for node in nodes}
    edges = [
        edge
        for edge in graph.get_edges()
        if edge.target_id is not None
        and edge.source_id in visible_ids
        and edge.target_id in visible_ids
    ]
    unresolved = [
        edge
        for edge in graph.get_edges()
        if edge.target_id is None and edge.source_id in visible_ids
    ]
    reference_nodes = {}
    for edge in unresolved:
        reference_id = f"reference:{edge.type.value}:{edge.target_ref}"
        reference_nodes[reference_id] = {
            "id": reference_id,
            "name": edge.target_ref,
            "kind": "reference",
            "qualified_name": edge.target_ref,
            "file": "unresolved reference",
            "location": None,
            "parent_id": None,
            "docstring": None,
            "metadata": {},
            "hash": None,
            "unresolved": True,
        }
    visual_edges = [_edge_dict(edge) for edge in edges]
    visual_edges.extend(
        {
            **_edge_dict(edge),
            "target": f"reference:{edge.type.value}:{edge.target_ref}",
            "unresolved": True,
        }
        for edge in unresolved
    )
    return {
        "nodes": [_node_dict(node, graph.get_node_hashes().get(node.id)) for node in nodes]
        + list(reference_nodes.values()),
        "edges": visual_edges,
        "unresolved_edges": [
            _edge_dict(edge) for edge in graph.get_edges() if edge.target_id is None
        ],
    }
