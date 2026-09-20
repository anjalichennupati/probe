import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from probe.builder.graph import Graph
from probe.builder.serialization import GraphSerializer
from probe.utils.logging import get_logger

logger = get_logger("probe.storage.file")


class StorageError(Exception):
    """Base error for persisted Probe state."""


class CorruptStorageError(StorageError):
    """Raised when persisted Probe JSON cannot be read or validated."""


@dataclass(frozen=True)
class NodeVersion:
    hash: str
    commit_id: str | None
    probed_at: str
    previous_hash: str | None


@dataclass
class NodeHistory:
    node_id: str
    versions: list[NodeVersion]


class Storage(Protocol):
    def save_graph(self, graph: Graph) -> None: ...

    def load_graph(self) -> Graph: ...

    def save_node_version(
        self,
        node_id: str,
        hash: str,
        commit_id: str | None,
        probed_at: str,
        previous_hash: str | None = None,
    ) -> None: ...

    def get_node_history(self, node_id: str) -> NodeHistory: ...

    def get_latest_node_version(self, node_id: str) -> NodeVersion | None: ...


class FileStorage:
    """Atomic JSON persistence for the current graph and node histories."""

    schema_version = 1

    def __init__(self, root: str | Path, project_name: str | None = None) -> None:
        self.root = Path(root)
        self.probe_dir = self.root / ".probe"
        if project_name:
            self.probe_dir /= project_name
        self.graph_path = self.probe_dir / "graph.json"
        self.metadata_path = self.probe_dir / "metadata.json"
        self.history_dir = self.probe_dir / "history"

    def exists(self) -> bool:
        return self.probe_dir.exists()

    def initialize(self) -> None:
        was_initialized = self.probe_dir.exists()
        self.history_dir.mkdir(parents=True, exist_ok=True)
        if not self.metadata_path.exists():
            self._write_json(self.metadata_path, {"schema_version": self.schema_version})
        if not self.graph_path.exists():
            self._write_json(self.graph_path, {"nodes": [], "edges": []})
        if was_initialized:
            logger.debug("Probe storage already initialized at %s", self.probe_dir)
        else:
            logger.info("Initialized Probe storage at %s", self.probe_dir)

    def save_graph(self, graph: Graph) -> None:
        self.initialize()
        self._write_json(self.graph_path, GraphSerializer.graph_to_dict(graph))
        logger.info("Saved graph to %s", self.graph_path)

    def load_graph(self) -> Graph:
        if not self.graph_path.exists():
            raise FileNotFoundError(f"Graph storage does not exist: {self.graph_path}")
        try:
            graph = GraphSerializer.graph_from_dict(self._read_json(self.graph_path, "graph"))
        except (KeyError, TypeError, ValueError) as exc:
            raise CorruptStorageError(f"Malformed graph: {self.graph_path}") from exc
        logger.info("Loaded graph from %s", self.graph_path)
        return graph

    def save_node_version(
        self,
        node_id: str,
        hash: str,
        commit_id: str | None,
        probed_at: str,
        previous_hash: str | None = None,
    ) -> None:
        self.initialize()
        history = self.get_node_history(node_id)
        latest = history.versions[-1] if history.versions else None
        if latest and latest.hash == hash:
            logger.info("Skipped unchanged node version for %s", node_id)
            return
        version = NodeVersion(
            hash=hash,
            commit_id=commit_id,
            probed_at=probed_at,
            previous_hash=latest.hash if latest else previous_hash,
        )
        history.versions.append(version)
        self._write_json(self._history_path(node_id), self._history_to_dict(history))
        logger.info("Saved node version %s for %s", hash, node_id)

    def get_node_history(self, node_id: str) -> NodeHistory:
        path = self._history_path(node_id)
        if not path.exists():
            return NodeHistory(node_id=node_id, versions=[])
        data = self._read_json(path, f"history for node {node_id}")
        try:
            if data["node_id"] != node_id:
                raise ValueError("node_id does not match requested history")
            versions = [NodeVersion(**version) for version in data["versions"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise CorruptStorageError(f"Malformed history for node {node_id}") from exc
        return NodeHistory(node_id=node_id, versions=versions)

    def get_latest_node_version(self, node_id: str) -> NodeVersion | None:
        history = self.get_node_history(node_id)
        return history.versions[-1] if history.versions else None

    def _history_path(self, node_id: str) -> Path:
        return self.history_dir / f"{node_id}.json"

    @staticmethod
    def _history_to_dict(history: NodeHistory) -> dict[str, object]:
        return {"node_id": history.node_id, "versions": [asdict(v) for v in history.versions]}

    @staticmethod
    def _read_json(path: Path, description: str) -> dict[str, object]:
        try:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("top-level JSON value must be an object")
            return data
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.error("Could not read %s: %s", description, path)
            raise CorruptStorageError(f"Malformed {description}: {path}") from exc

    @staticmethod
    def _write_json(path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
