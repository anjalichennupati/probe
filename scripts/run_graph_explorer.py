# ruff: noqa: I001

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from probe_ui import GraphExplorer


PROJECT_NAME = "probe"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORT = 8000


def main() -> None:
    GraphExplorer(PROJECT_NAME, root=PROJECT_ROOT, port=PORT).serve()


if __name__ == "__main__":
    main()
