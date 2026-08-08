"""Local dev server that emulates the Vercel runtime.

Serves static files from public/ and routes /api/* to the Vercel
serverless handlers in api/ (the exact code deployed to Vercel).

Usage:
    venv/bin/python local/dev_server.py
"""
import importlib
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
API = ROOT / "api"

load_dotenv(ROOT / ".env")

# Ensure repo root is importable so `services.*` resolves.
sys.path.insert(0, str(ROOT))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def _handle_api(self, path: str):
        # Map /api/ask -> api/ask.py, /api/history -> api/history.py, etc.
        name = path.split("/")[-1]
        module_name = f"api.{name}"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"detail": "Not found"}')
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        class FakeRequest:
            def json(self):
                return json.loads(body or b"{}")

        try:
            result = module.handler(FakeRequest())
            if isinstance(result, tuple):
                payload, status = result
            else:
                payload, status = result, 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": str(exc)}).encode("utf-8"))

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._handle_api(self.path)
            return
        # Emulate vercel.json rewrites: /question-log -> /question-log.html
        clean = self.path.split("?", 1)[0]
        if clean in ("/question-log", "/bedtime-story"):
            self.path = clean + ".html"
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._handle_api(self.path)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[dev] {fmt % args}\n")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Dev server (Vercel emulation) on http://127.0.0.1:{port}")
    print(f"  Landing page: http://127.0.0.1:{port}/")
    server.serve_forever()