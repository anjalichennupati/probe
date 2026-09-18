import json
import os
import sys
from dataclasses import asdict

# Ensure repository root is in sys.path for standalone script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from probe.model.models import EdgeType, NodeType
from probe.parser import ParserRegistry, PythonParser, detect_language


def test_detect_language() -> None:
    assert detect_language("app.py") == "python"
    assert detect_language("utils.pyi") == "python"
    assert detect_language("index.ts") == "typescript"
    assert detect_language("main.go") == "go"
    assert detect_language("unknown.txt") is None


def test_parser_registry() -> None:
    registry = ParserRegistry()
    parser = PythonParser()
    registry.register(parser)

    assert registry.get_parser("python") == parser
    assert registry.get_parser_for_file("math_utils.py") == parser
    assert registry.get_parser_for_file("main.go") is None


def test_python_parser_basic() -> None:
    code = '''"""Module docstring."""
import os
from math import sqrt

class Shape:
    """Base shape class."""
    pass

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14 * sqrt(self.radius)

def main():
    c = Circle(5.0)
    print(c.area())
'''
    parser = PythonParser()
    result = parser.parse_file("graphics/shapes.py", content=code)

    assert len(result.errors) == 0
    assert result.file_path == "graphics/shapes.py"

    # Print raw JSON output of ParseResult
    print("--- PARSER JSON OUTPUT ---")
    print(json.dumps(asdict(result), indent=2))
    print("--------------------------")

    # Verify Nodes
    node_types = [n.type for n in result.nodes]
    assert NodeType.FILE in node_types
    assert NodeType.CLASS in node_types
    assert NodeType.METHOD in node_types
    assert NodeType.FUNCTION in node_types

    # Find specific nodes
    root_node = next(n for n in result.nodes if n.type == NodeType.FILE)
    assert root_node.docstring == "Module docstring."

    circle_node = next(n for n in result.nodes if n.name == "Circle")
    assert circle_node.type == NodeType.CLASS
    assert circle_node.detailed_name == "graphics.shapes.Circle"

    area_node = next(n for n in result.nodes if n.name == "area")
    assert area_node.type == NodeType.METHOD
    assert area_node.parent_id == circle_node.id

    main_node = next(n for n in result.nodes if n.name == "main")
    assert main_node.type == NodeType.FUNCTION

    # Verify Edges
    edge_types = [e.type for e in result.edges]
    assert EdgeType.CONTAINS in edge_types
    assert EdgeType.INHERITS in edge_types
    assert EdgeType.IMPORTS in edge_types
    assert EdgeType.CALLS in edge_types

    # Inheritance edge: Circle -> Shape
    inherits_edge = next(e for e in result.edges if e.type == EdgeType.INHERITS)
    assert inherits_edge.source_id == circle_node.id
    assert inherits_edge.target_id == "Shape"

    # Imports edges
    import_targets = [e.target_id for e in result.edges if e.type == EdgeType.IMPORTS]
    assert "os" in import_targets
    assert "math.sqrt" in import_targets

    # Calls edges (area() calls sqrt)
    call_edges = [e for e in result.edges if e.type == EdgeType.CALLS]
    caller_ids = [e.source_id for e in call_edges]
    assert area_node.id in caller_ids


def test_python_parser_syntax_error() -> None:
    bad_code = "def broken_func("
    parser = PythonParser()
    result = parser.parse_file("broken.py", content=bad_code)

    assert len(result.errors) == 1
    assert "SyntaxError" in result.errors[0]


if __name__ == "__main__":
    print("Running PythonParser tests in scripts/...")
    test_detect_language()
    test_parser_registry()
    test_python_parser_basic()
    test_python_parser_syntax_error()
    print("All tests passed successfully!")
