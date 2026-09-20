import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class NodeType(StrEnum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"


class EdgeType(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    REFERENCES = "references"


@dataclass
class LocationSpan:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


def generate_node_id(file_path: str, detailed_name: str, node_type: Any) -> str:
    """Generates a deterministic 16-character SHA-256 hash ID for a node."""
    type_str = node_type.value if hasattr(node_type, "value") else str(node_type)
    raw_key = f"{file_path}::{detailed_name}::{type_str}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


@dataclass
class Node:
    id: str
    type: NodeType
    name: str
    detailed_name: str
    file_path: str
    parent_id: str | None = None
    span: LocationSpan | None = None
    docstring: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    source_id: str
    target_id: str | None
    target_ref: str | None
    type: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    file_path: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
