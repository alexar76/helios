"""Health HTTP server — GET /health only (security: no request body parsing)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

from helios import __version__


class _HealthHandler(BaseHTTPRequestHandler):
    get_snapshot: Callable[[], dict[str, Any]]

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        path = (self.path or "/").split("?")[0]
        if path == "/health":
            try:
                snap = self.get_snapshot()
                body = json.dumps({"ok": True, "version": __version__, **snap}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"ok":false}')
            return
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":false}')


def create_health_server(port: int, get_snapshot: Callable[[], dict[str, Any]]) -> HTTPServer:
    handler = type("Handler", (_HealthHandler,), {"get_snapshot": staticmethod(get_snapshot)})
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
