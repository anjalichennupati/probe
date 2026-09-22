# ruff: noqa: I001

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from probe.builder import GraphBuilder
from probe.parser import PythonParser
from probe_ui import graph_payload, node_payload


def test_graph_explorer_payload_preserves_semantic_edges() -> None:
    result = PythonParser().parse_file(
        "payments/service.py",
        content="""\
class PaymentService:
    def charge(self):
        return PaymentGateway.pay()
""",
    )
    graph = GraphBuilder().build(result)

    payload = graph_payload(graph)
    method = next(node for node in graph.get_nodes() if node.name == "charge")
    details = node_payload(graph, method.id)

    assert {node["name"] for node in payload["nodes"]} == {
        "service.py",
        "PaymentService",
        "charge",
        "PaymentGateway.pay",
    }
    assert any(edge["type"] == "contains" for edge in payload["edges"])
    assert any(
        edge["type"] == "calls" and edge["target_ref"] == "PaymentGateway.pay"
        for edge in payload["edges"]
    )
    assert details is not None
    assert details["node"]["qualified_name"].endswith("PaymentService.charge")
    assert details["node"]["hash"] == graph.get_node_hashes()[method.id]
    assert details["outgoing"][0]["target_ref"] == "PaymentGateway.pay"
    assert payload["unresolved_edges"][0]["target_ref"] == "PaymentGateway.pay"


if __name__ == "__main__":
    test_graph_explorer_payload_preserves_semantic_edges()
    print("Graph Explorer adapter check passed")
