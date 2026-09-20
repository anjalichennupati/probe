from typing import Any

from probe.builder.graph import Graph, NodeContent
from probe.model.models import Edge, EdgeType, LocationSpan, Node, NodeType
from probe.utils.logging import get_logger

logger = get_logger("probe.builder.serialization")


class GraphSerializer:
    """Convert graph models to and from explicit JSON-compatible dictionaries."""

    @staticmethod
    def node_to_dict(node: Node) -> dict[str, Any]:
        return NodeContent.from_node(node).to_dict()

    @staticmethod
    def node_from_dict(data: dict[str, Any]) -> Node:
        span_data = data.get("span")
        return Node(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data["name"],
            detailed_name=data["detailed_name"],
            file_path=data["file_path"],
            parent_id=data.get("parent_id"),
            span=LocationSpan(**span_data) if span_data else None,
            docstring=data.get("docstring"),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def edge_to_dict(edge: Edge) -> dict[str, Any]:
        return {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "target_ref": edge.target_ref,
            "type": edge.type.value,
            "metadata": edge.metadata,
        }

    @staticmethod
    def edge_from_dict(data: dict[str, Any]) -> Edge:
        return Edge(
            source_id=data["source_id"],
            target_id=data.get("target_id"),
            target_ref=data.get("target_ref"),
            type=EdgeType(data["type"]),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def graph_to_dict(cls, graph: Graph) -> dict[str, Any]:
        logger.debug("Serializing graph with %d nodes", len(graph.get_nodes()))
        return {
            "nodes": [cls.node_to_dict(node) for node in graph.get_nodes()],
            "edges": [cls.edge_to_dict(edge) for edge in graph.get_edges()],
        }

    @classmethod
    def graph_from_dict(cls, data: dict[str, Any]) -> Graph:
        graph = Graph()
        nodes = data.get("nodes")
        edges = data.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("Graph data must contain nodes and edges lists")
        for node_data in nodes:
            node = cls.node_from_dict(node_data)
            graph._add_node(node, NodeContent.from_node(node).content_hash())
        for edge_data in edges:
            graph._add_edge(cls.edge_from_dict(edge_data))
        logger.debug("Deserialized graph with %d nodes", len(graph.get_nodes()))
        return graph
