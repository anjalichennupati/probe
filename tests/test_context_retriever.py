from probe.builder.graph import Graph
from probe.context import (
    ContextCandidate,
    ContextEngine,
    ContextLines,
    ContextPackage,
    ContextRequest,
    ContextResponse,
    ContextSnippet,
    discover_candidates,
)
from probe.model.models import Edge, EdgeType, LocationSpan, Node, NodeType


def _make_graph() -> Graph:
    graph = Graph()
    file_node = Node(
        id="file-1",
        type=NodeType.FILE,
        name="service.py",
        detailed_name="service",
        file_path="/tmp/service.py",
        parent_id=None,
        span=LocationSpan(1, 0, 10, 0),
    )
    service_cls = Node(
        id="class-1",
        type=NodeType.CLASS,
        name="Service",
        detailed_name="service.Service",
        file_path="/tmp/service.py",
        parent_id=file_node.id,
        span=LocationSpan(1, 0, 8, 0),
    )
    method = Node(
        id="method-1",
        type=NodeType.METHOD,
        name="run",
        detailed_name="service.Service.run",
        file_path="/tmp/service.py",
        parent_id=service_cls.id,
        span=LocationSpan(2, 4, 6, 11),
    )
    helper = Node(
        id="func-1",
        type=NodeType.FUNCTION,
        name="helper",
        detailed_name="service.helper",
        file_path="/tmp/service.py",
        parent_id=file_node.id,
        span=LocationSpan(8, 0, 10, 0),
    )

    graph._add_node(file_node, "hash-file")
    graph._add_node(service_cls, "hash-class")
    graph._add_node(method, "hash-method")
    graph._add_node(helper, "hash-func")

    graph._add_edge(Edge(file_node.id, service_cls.id, None, EdgeType.CONTAINS))
    graph._add_edge(Edge(service_cls.id, method.id, None, EdgeType.CONTAINS))
    graph._add_edge(Edge(file_node.id, helper.id, None, EdgeType.CONTAINS))
    graph._add_edge(Edge(method.id, helper.id, None, EdgeType.CALLS, metadata={"call": "helper"}))

    return graph


def test_discover_candidates_traverses_graph():
    graph = _make_graph()

    candidates = discover_candidates(graph, ["class-1"], depth=2, max_candidates=10)

    assert {candidate.entity_id for candidate in candidates} >= {"method-1", "func-1"}
    assert any(candidate.entity_id == "method-1" for candidate in candidates)


def test_context_engine_assembles_snippets_for_target_request(tmp_path):
    source_file = tmp_path / "service.py"
    source_file.write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        return helper()\n\n"
        "def helper():\n"
        "    return 42\n",
        encoding="utf-8",
    )

    graph = Graph()
    file_node = Node(
        id="file-1",
        type=NodeType.FILE,
        name="service.py",
        detailed_name="service",
        file_path=str(source_file),
        parent_id=None,
        span=LocationSpan(1, 0, 7, 0),
    )
    service_cls = Node(
        id="class-1",
        type=NodeType.CLASS,
        name="Service",
        detailed_name="service.Service",
        file_path=str(source_file),
        parent_id=file_node.id,
        span=LocationSpan(1, 0, 3, 19),
    )
    method = Node(
        id="method-1",
        type=NodeType.METHOD,
        name="run",
        detailed_name="service.Service.run",
        file_path=str(source_file),
        parent_id=service_cls.id,
        span=LocationSpan(2, 4, 3, 24),
    )
    helper = Node(
        id="func-1",
        type=NodeType.FUNCTION,
        name="helper",
        detailed_name="service.helper",
        file_path=str(source_file),
        parent_id=file_node.id,
        span=LocationSpan(5, 0, 6, 11),
    )

    graph._add_node(file_node, "hash-file")
    graph._add_node(service_cls, "hash-class")
    graph._add_node(method, "hash-method")
    graph._add_node(helper, "hash-func")

    graph._add_edge(Edge(file_node.id, service_cls.id, None, EdgeType.CONTAINS))
    graph._add_edge(Edge(service_cls.id, method.id, None, EdgeType.CONTAINS))
    graph._add_edge(Edge(file_node.id, helper.id, None, EdgeType.CONTAINS))
    graph._add_edge(Edge(method.id, helper.id, None, EdgeType.CALLS, metadata={"call": "helper"}))

    request = ContextRequest(
        retrieval_mode="target",
        target_id="class-1",
        depth=2,
        max_candidates=10,
        max_snippets=2,
        context_budget=5000,
        semantic_ranking=False,
    )
    package = ContextEngine(graph=graph).run(request)

    assert package.candidates
    assert package.snippets
    assert package.snippets[0].path == str(source_file)
    assert any("return helper()" in snippet.text for snippet in package.snippets)
    assert package.candidates[0].source.file == str(source_file)
    assert package.snippets[0].lines.start >= 1
    assert package.summary.candidate_count == len(package.candidates)


def test_context_package_to_dict_is_json_safe():
    package = ContextPackage(
        request=ContextRequest(
            retrieval_mode="target",
            target_id="node-1",
            depth=1,
            max_candidates=2,
            max_snippets=1,
            context_budget=1000,
            semantic_ranking=False,
        ),
        candidates=[
            ContextCandidate(
                entity_id="node-1",
                entity_type="method",
                graph_distance=0,
                score=0.5,
                rationale="direct match",
            )
        ],
        snippets=[
            ContextSnippet(
                entity_id="node-1",
                path="/tmp/example.py",
                lines=ContextLines(start=1, end=3),
                text="def example():\n    return 1\n",
                score=0.5,
                rationale="direct match",
            )
        ],
    )

    payload = package.to_dict()
    response = package.to_response()

    assert isinstance(response, ContextResponse)
    assert response.request.mode == "target"
    assert response.summary.candidate_count == 1
    assert payload["schema_version"] == 1
    assert payload["status"] == "partial"
    assert payload["request"]["target_id"] == "node-1"
    assert payload["summary"]["candidate_count"] == 1
    assert payload["candidates"][0]["entity_id"] == "node-1"
    assert payload["snippets"][0]["path"] == "/tmp/example.py"
    assert payload["snippets"][0]["lines"]["start"] == 1
