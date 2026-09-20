import subprocess
from datetime import UTC, datetime
from pathlib import Path

from probe.builder import FileStorage, Graph, GraphBuilder
from probe.model.models import ParseResult
from probe.parser import ParserRegistry, PythonParser, detect_language
from probe.utils.logging import get_logger

logger = get_logger("probe.project")


def current_commit(root: Path) -> str | None:
    """Return the repository HEAD commit, or None outside a Git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        logger.debug("No Git commit found for %s", root)
        return None
    return result.stdout.strip() or None


class ProbeProject:
    """Public project facade connecting parsing, graph building, and storage."""

    def __init__(self, project_name: str, root: str | Path) -> None:
        self.project_name = project_name
        self.root = Path(root).resolve()
        self.storage = FileStorage(self.root, project_name=project_name)
        self.parsers = ParserRegistry()
        self.parsers.register(PythonParser())

    def initialize(self) -> None:
        self.storage.initialize()
        logger.info("Initialized project %s at %s", self.project_name, self.root)

    def parse(self, file_path: str | Path) -> ParseResult:
        path = Path(file_path)
        absolute_path = path if path.is_absolute() else self.root / path
        parser = self.parsers.get_parser_for_file(str(absolute_path))
        if parser is None:
            raise ValueError(f"No parser registered for file: {absolute_path}")
        logger.info("Parsing project file %s", absolute_path)
        return parser.parse_file(str(absolute_path))

    def _parse_path(self, target: str | Path) -> ParseResult:
        path = Path(target)
        absolute_path = path if path.is_absolute() else self.root / path
        if absolute_path.is_file():
            return self.parse(absolute_path)
        if not absolute_path.is_dir():
            raise FileNotFoundError(f"Build path does not exist: {absolute_path}")

        combined = ParseResult(file_path=str(absolute_path))
        for file_path in sorted(absolute_path.rglob("*")):
            if not file_path.is_file() or any(part.startswith(".") for part in file_path.parts):
                continue
            if detect_language(str(file_path)) is None:
                continue
            result = self.parse(file_path)
            combined.nodes.extend(result.nodes)
            combined.edges.extend(result.edges)
            combined.errors.extend(result.errors)
        return combined

    def _build_graph(self, parse_result: ParseResult) -> Graph:
        return GraphBuilder().build(parse_result)

    def build(self, target: str | Path | ParseResult) -> Graph:
        """Build and persist a knowledge graph from a file, repository, or result."""
        parse_result = target if isinstance(target, ParseResult) else self._parse_path(target)
        return self.persist(parse_result)

    def persist(self, parse_result: ParseResult) -> Graph:
        """Build, persist, and version an existing parser result."""
        graph = self._build_graph(parse_result)
        self.storage.save_graph(graph)
        commit_id = current_commit(self.root)
        probed_at = datetime.now(UTC).isoformat()
        for node in graph.get_nodes():
            self.storage.save_node_version(
                node.id,
                graph.get_node_hashes()[node.id],
                commit_id=commit_id,
                probed_at=probed_at,
            )
        logger.info(
            "Analyzed %s: %d nodes, %d edges, commit=%s",
            parse_result.file_path,
            len(graph.get_nodes()),
            len(graph.get_edges()),
            commit_id,
        )
        return graph

    def analyze(self, file_path: str | Path) -> Graph:
        """Parse, build, persist, and version one source file's current graph."""
        return self.build(file_path)


def init(project_name: str, root: str | Path | None = None) -> ProbeProject:
    """Initialize a Probe project rooted at the current directory by default."""
    project = ProbeProject(project_name, root or Path.cwd())
    project.initialize()
    return project
