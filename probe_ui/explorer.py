from http.server import ThreadingHTTPServer
from pathlib import Path

from probe import ProbeProject
from probe_ui.server import create_handler


class GraphExplorer:
    """Serve the persisted graph for one named Probe project."""

    def __init__(
        self,
        project_name: str,
        root: str | Path = ".",
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.project = ProbeProject(project_name, root)
        self.graph = self.project.storage.load_graph()
        self.host = host
        self.port = port

    def serve(self) -> None:
        server = ThreadingHTTPServer((self.host, self.port), create_handler(self.graph))
        print(f"Probe Graph Explorer: http://{self.host}:{self.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
