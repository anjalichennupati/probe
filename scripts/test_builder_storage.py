# ruff: noqa: I001

import logging
import os
import sys
from pathlib import Path

# Ensure repository root is in sys.path for standalone script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from probe import init


PROJECT_NAME = "probe"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = PROJECT_ROOT / "tests" / "test_setup.py"


def main() -> None:
    """Build the configured sample file through the public Probe API."""
    logging.disable(logging.CRITICAL)
    project = init(project_name=PROJECT_NAME, root=PROJECT_ROOT)
    graph = project.build(TARGET_PATH)

    print(f"Built graph: {len(graph.get_nodes())} nodes, {len(graph.get_edges())} edges")
    print(f"Input path: {TARGET_PATH}")
    print(f"Storage: {project.storage.probe_dir}")


if __name__ == "__main__":
    main()
