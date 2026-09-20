# ruff: noqa: I001

import logging
import sys
from pathlib import Path

# Allow this example to run directly from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from probe import init


PROJECT_NAME = "hello"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = Path("/Users/anjalichennupati/ML/probe/probe/tests/test_setup.py")


def main() -> None:
    logging.disable(logging.CRITICAL)
    project = init(project_name=PROJECT_NAME, root=PROJECT_ROOT)
    graph = project.build(TARGET_PATH)

    print(f"Built graph: {len(graph.get_nodes())} nodes, {len(graph.get_edges())} edges")
    print(f"Input path: {TARGET_PATH}")
    print(f"Probe storage: {project.storage.probe_dir}")


if __name__ == "__main__":
    main()
