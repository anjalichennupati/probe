import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from probe.model.models import Edge, Node, ParseResult
from probe.utils.logging import get_logger

logger = get_logger("probe.builder.graph")


class Graph:
    """In-memory representation of the current Probe graph."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._outgoing: dict[str, list[Edge]] = {}
        self._incoming: dict[str, list[Edge]] = {}
        self._node_hashes: dict[str, str] = {}

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def get_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def get_edges(self) -> list[Edge]:
        return list(self._edges)

    def get_outgoing(self, node_id: str) -> list[Edge]:
        return list(self._outgoing.get(node_id, []))

    def get_incoming(self, node_id: str) -> list[Edge]:
        return list(self._incoming.get(node_id, []))

    def get_node_hashes(self) -> dict[str, str]:
        return dict(self._node_hashes)

    def _add_node(self, node: Node, node_hash: str) -> None:
        if node.id in self._nodes:
            logger.error("Duplicate node ID detected: %s", node.id)
            raise ValueError(f"Duplicate node ID: {node.id}")
        self._nodes[node.id] = node
        self._node_hashes[node.id] = node_hash

    def _add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self._nodes:
            logger.error("Edge source ID does not exist: %s", edge.source_id)
            raise ValueError(f"Edge source_id does not exist: {edge.source_id}")
        if edge.target_id is not None and edge.target_id not in self._nodes:
            logger.error("Edge target ID does not exist: %s", edge.target_id)
            raise ValueError(f"Edge target_id does not exist: {edge.target_id}")
        self._edges.append(edge)
        self._outgoing.setdefault(edge.source_id, []).append(edge)
        if edge.target_id is not None:
            self._incoming.setdefault(edge.target_id, []).append(edge)


@dataclass(frozen=True)
class NodeContent:
    """Stable, meaningful content used for node serialization and hashing."""

    id: str
    type: str
    name: str
    detailed_name: str
    file_path: str
    parent_id: str | None
    span: dict[str, int] | None
    docstring: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_node(cls, node: Node) -> "NodeContent":
        return cls(
            id=node.id,
            type=node.type.value,
            name=node.name,
            detailed_name=node.detailed_name,
            file_path=node.file_path,
            parent_id=node.parent_id,
            span=asdict(node.span) if node.span else None,
            docstring=node.docstring,
            metadata=node.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def content_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class GraphBuilder:
    """Build a language-agnostic graph from normalized parser output."""

    def build(self, parse_result: ParseResult) -> Graph:
        logger.info(
            "Building graph from %d nodes and %d edges",
            len(parse_result.nodes),
            len(parse_result.edges),
        )
        graph = Graph()
        for node in parse_result.nodes:
            graph._add_node(node, NodeContent.from_node(node).content_hash())
        for edge in parse_result.edges:
            graph._add_edge(edge)
        logger.info(
            "Graph built with %d nodes and %d edges",
            len(graph.get_nodes()),
            len(graph.get_edges()),
        )
        return graph
