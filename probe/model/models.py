from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"


class EdgeType(str, Enum):
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
    target_id: str
    type: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict)
