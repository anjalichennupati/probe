from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from probe.context import ContextEngine, ContextRequest  # noqa: E402
from probe.project import ProbeProject  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run context retrieval against a saved Probe graph and real source files."
    )
    parser.add_argument(
        "--project",
        default="probe",
        help="Project name under .probe (default: probe).",
    )
    parser.add_argument(
        "--target",
        default="PythonParser.parse_file",
        help="Node ID, exact name, or detailed-name suffix (default: PythonParser.parse_file).",
    )
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--max-snippets", type=int, default=5)
    parser.add_argument(
        "--semantic-ranking",
        action="store_true",
        help=(
            "Rank candidates with the configured LLM provider (requires OPENROUTER_API_KEY); "
            "exit with an error if ranking falls back."
        ),
    )
    return parser.parse_args()


def find_target(graph, identifier: str):
    node = graph.get_node(identifier)
    if node is not None:
        return node
    matches = [
        candidate
        for candidate in graph.get_nodes()
        if candidate.name == identifier
        or candidate.detailed_name == identifier
        or candidate.detailed_name.endswith(f".{identifier}")
    ]
    if not matches:
        raise ValueError(f"No graph node matches target {identifier!r}.")
    return matches[0]


def main() -> None:
    args = parse_args()
    project = ProbeProject(project_name=args.project, root=PROJECT_ROOT)
    graph = project.storage.load_graph()
    target = find_target(graph, args.target)
    if not Path(target.file_path).is_file():
        raise FileNotFoundError(
            f"Target source file is missing: {target.file_path}. "
            "Rebuild this Probe graph from the current checkout."
        )

    request = ContextRequest(
        retrieval_mode="target",
        target_id=target.id,
        depth=args.depth,
        max_candidates=25,
        max_snippets=args.max_snippets,
        context_budget=12000,
        semantic_ranking=args.semantic_ranking,
    )

    package = ContextEngine(graph=graph).run(request)
    print(package.to_json(indent=2, sort_keys=True))
    if args.semantic_ranking and package.fallback_used:
        print(
            "Semantic ranking failed; structural fallback was used. "
            "See the warning above for the failure type.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
