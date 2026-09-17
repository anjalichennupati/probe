import ast
import os
from typing import Any, Dict, List, Optional

from probe.model.models import (
    Edge,
    EdgeType,
    LocationSpan,
    Node,
    NodeType,
    ParseResult,
    generate_node_id,
)
from probe.parser.base import BaseParser
from probe.utils.logging import get_logger

logger = get_logger("probe.parser.python")


def _get_location_span(node: ast.AST) -> Optional[LocationSpan]:
    """Extracts LocationSpan from an AST node if line numbers are present."""
    start_line = getattr(node, "lineno", None)
    start_col = getattr(node, "col_offset", None)
    end_line = getattr(node, "end_lineno", start_line)
    end_col = getattr(node, "end_col_offset", start_col)

    if start_line is not None and start_col is not None:
        return LocationSpan(
            start_line=start_line,
            start_column=start_col,
            end_line=end_line if end_line is not None else start_line,
            end_column=end_col if end_col is not None else start_col,
        )
    return None


def _get_name_from_attribute(node: ast.AST) -> str:
    """Helper to convert complex attribute calls (e.g., self.foo or os.path.join) into string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        value_str = _get_name_from_attribute(node.value)
        return f"{value_str}.{node.attr}" if value_str else node.attr
    return ""


class PythonASTVisitor(ast.NodeVisitor):
    """AST Visitor to extract Probe Nodes and Edges from a Python syntax tree."""

    def __init__(self, file_path: str, code_content: str) -> None:
        self.file_path = file_path
        self.code_content = code_content
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []
        self.errors: List[str] = []

        # Derive module detailed_name from file path without regex
        rel_path = os.path.normpath(file_path)
        module_detailed_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
        if module_detailed_name.startswith("."):
            module_detailed_name = module_detailed_name.lstrip(".")

        # Root FILE node
        file_node_id = generate_node_id(self.file_path, module_detailed_name, NodeType.FILE)
        docstring = ast.get_docstring(ast.parse(code_content)) if code_content.strip() else None

        lines = code_content.splitlines()
        file_span = LocationSpan(
            start_line=1,
            start_column=0,
            end_line=max(1, len(lines)),
            end_column=len(lines[-1]) if lines else 0,
        )

        self.root_node = Node(
            id=file_node_id,
            type=NodeType.FILE,
            name=os.path.basename(file_path),
            detailed_name=module_detailed_name,
            file_path=self.file_path,
            parent_id=None,
            span=file_span,
            docstring=docstring,
        )
        self.nodes.append(self.root_node)

        # Scope stack tracks parent nodes and detailed names during traversal
        self.scope_stack: List[Node] = [self.root_node]

    @property
    def current_parent(self) -> Node:
        return self.scope_stack[-1]

    def _build_detailed_name(self, name: str) -> str:
        parent_detailed_name = self.current_parent.detailed_name
        return f"{parent_detailed_name}.{name}" if parent_detailed_name else name

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        dname = self._build_detailed_name(node.name)
        node_id = generate_node_id(self.file_path, dname, NodeType.CLASS)
        span = _get_location_span(node)
        docstring = ast.get_docstring(node)

        class_node = Node(
            id=node_id,
            type=NodeType.CLASS,
            name=node.name,
            detailed_name=dname,
            file_path=self.file_path,
            parent_id=self.current_parent.id,
            span=span,
            docstring=docstring,
        )
        self.nodes.append(class_node)

        # CONTAINS edge (Parent -> Class)
        self.edges.append(
            Edge(
                source_id=self.current_parent.id,
                target_id=class_node.id,
                type=EdgeType.CONTAINS,
            )
        )

        # INHERITS edges
        for base in node.bases:
            base_name = _get_name_from_attribute(base)
            if base_name:
                self.edges.append(
                    Edge(
                        source_id=class_node.id,
                        target_id=base_name,
                        type=EdgeType.INHERITS,
                    )
                )

        self.scope_stack.append(class_node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def _visit_function(self, node: ast.AST, name: str, is_async: bool = False) -> None:
        dname = self._build_detailed_name(name)
        node_type = (
            NodeType.METHOD
            if self.current_parent.type == NodeType.CLASS
            else NodeType.FUNCTION
        )
        node_id = generate_node_id(self.file_path, dname, node_type)
        span = _get_location_span(node)
        docstring = ast.get_docstring(node)

        func_node = Node(
            id=node_id,
            type=node_type,
            name=name,
            detailed_name=dname,
            file_path=self.file_path,
            parent_id=self.current_parent.id,
            span=span,
            docstring=docstring,
            metadata={"async": is_async},
        )
        self.nodes.append(func_node)

        # CONTAINS edge (Parent -> Function/Method)
        self.edges.append(
            Edge(
                source_id=self.current_parent.id,
                target_id=func_node.id,
                type=EdgeType.CONTAINS,
            )
        )

        self.scope_stack.append(func_node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, node.name, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, node.name, is_async=True)

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_parent.type in (NodeType.FUNCTION, NodeType.METHOD):
            func_name = _get_name_from_attribute(node.func)
            if func_name:
                self.edges.append(
                    Edge(
                        source_id=self.current_parent.id,
                        target_id=func_name,
                        type=EdgeType.CALLS,
                    )
                )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.edges.append(
                Edge(
                    source_id=self.root_node.id,
                    target_id=alias.name,
                    type=EdgeType.IMPORTS,
                    metadata={"alias": alias.asname} if alias.asname else {},
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.edges.append(
                Edge(
                    source_id=self.root_node.id,
                    target_id=full_name,
                    type=EdgeType.IMPORTS,
                    metadata={"module": module, "alias": alias.asname} if alias.asname else {"module": module},
                )
            )


class PythonParser(BaseParser):
    """Concrete BaseParser implementation for Python using built-in AST."""

    @property
    def language(self) -> str:
        return "python"

    def load_language(self, language: Optional[str] = None) -> None:
        logger.debug("Initializing Python AST Parser environment")

    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParseResult:
        logger.info(f"Parsing Python file [cyan]{file_path}[/cyan]")

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                error_msg = f"File read error: {str(e)}"
                logger.error(f"Failed to read [red]{file_path}[/red]: {error_msg}")
                return ParseResult(file_path=file_path, errors=[error_msg])

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as se:
            error_msg = f"SyntaxError at line {se.lineno}, col {se.offset}: {se.msg}"
            logger.warning(f"Syntax error in [yellow]{file_path}[/yellow]: {error_msg}")
            return ParseResult(
                file_path=file_path,
                errors=[error_msg],
            )

        visitor = PythonASTVisitor(file_path, content)
        visitor.visit(tree)

        logger.info(
            f"Successfully parsed [cyan]{file_path}[/cyan] "
            f"([bold green]{len(visitor.nodes)}[/bold green] nodes, "
            f"[bold blue]{len(visitor.edges)}[/bold blue] edges)"
        )

        return ParseResult(
            file_path=file_path,
            nodes=visitor.nodes,
            edges=visitor.edges,
            errors=visitor.errors,
        )
