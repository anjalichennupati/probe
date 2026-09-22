import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from probe_ui.adapter import graph_payload, node_payload

_UI_ROOT = Path(__file__).parent


def create_handler(graph):
    class ExplorerHandler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str, content_type: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/graph":
                params = parse_qs(parsed.query)
                raw_limit = params.get("limit", [None])[0]
                limit = int(raw_limit) if raw_limit else None
                self._send(200, json.dumps(graph_payload(graph, limit)), "application/json")
                return
            if parsed.path.startswith("/api/node/"):
                payload = node_payload(graph, parsed.path.removeprefix("/api/node/"))
                if payload is None:
                    self._send(404, json.dumps({"error": "node not found"}), "application/json")
                else:
                    self._send(200, json.dumps(payload), "application/json")
                return
            if parsed.path in ("/", "/index.html"):
                self._send(200, (_UI_ROOT / "index.html").read_text(), "text/html")
                return
            if parsed.path == "/app.js":
                self._send(200, (_UI_ROOT / "app.js").read_text(), "text/javascript")
                return
            if parsed.path == "/styles.css":
                self._send(200, (_UI_ROOT / "styles.css").read_text(), "text/css")
                return
            self._send(404, "Not found", "text/plain")

        def log_message(self, format: str, *args: object) -> None:
            return

    return ExplorerHandler
