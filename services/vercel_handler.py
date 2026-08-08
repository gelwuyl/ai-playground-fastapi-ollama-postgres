"""Base class for Vercel Python serverless functions.

Vercel's Python runtime requires each api/*.py file to expose a top-level
`handler` that subclasses `http.server.BaseHTTPRequestHandler`. This base
class provides JSON request parsing and JSON response helpers so the
individual endpoint files stay small.
"""
import json
from http.server import BaseHTTPRequestHandler


class VercelHandler(BaseHTTPRequestHandler):
    """Base handler with JSON helpers for Vercel serverless functions."""

    def read_json(self):
        """Parse the request body as JSON. Raises on invalid JSON."""
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        return json.loads(body or b"{}")

    def json_response(self, payload, status=200):
        """Send a JSON response."""
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):  # noqa: A002 - silence request logs
        pass