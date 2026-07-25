"""Local web dashboard server for Smart Organizer."""

from __future__ import annotations

import json
import queue
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from organizer_core import app_data_dir, execute, save_undo_log, scan, undo

APP_NAME = "Smart File Organizer"
DEFAULT_PORT = 8787


def frozen_base_path() -> Path:
    """Return the folder that contains bundled assets in source or PyInstaller mode."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def asset_path(name: str) -> Path:
    return frozen_base_path() / name


class OrganizerServer(ThreadingHTTPServer):
    def __init__(self, server_address, request_handler, portable: bool = True):
        super().__init__(server_address, request_handler)
        self.data_dir = app_data_dir(portable=portable)
        self.last_plan: list[dict] = []
        self.shutdown_requested = threading.Event()


class Handler(BaseHTTPRequestHandler):
    server: OrganizerServer

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        return

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html = asset_path("frontend.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if parsed.path == "/assets/tailwind-offline.css":
            css = asset_path("assets/tailwind-offline.css").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(css)))
            self.end_headers()
            self.wfile.write(css)
            return
        if parsed.path == "/api/scan-stream":
            self._scan_stream(parse_qs(parsed.query))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/execute":
            payload = self._read_json()
            plan = payload.get("plan") or self.server.last_plan
            result = execute(plan, bool(payload.get("skipDuplicates")))
            save_undo_log(self.server.data_dir, result)
            self._send_json(result)
            return
        if self.path == "/api/undo":
            self._send_json(undo(self.server.data_dir))
            return
        if self.path == "/api/shutdown":
            self._send_json({"ok": True})
            self.server.shutdown_requested.set()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _scan_stream(self, query: dict[str, list[str]]) -> None:
        source = Path(query.get("source", [str(Path.home() / "Downloads")])[0]).expanduser()
        target = Path(query.get("target", [str(source / "Organized")])[0]).expanduser()
        conflict_mode = query.get("conflict", ["rename"])[0]
        events: queue.Queue[dict | None] = queue.Queue()

        def progress(event: dict) -> None:
            events.put(event)

        def worker() -> None:
            try:
                report = scan(source, target, conflict_mode, progress)
                self.server.last_plan = [item.__dict__ for item in report.files if not item.error]
            except Exception as exc:  # keep SSE alive for unexpected failures
                events.put({"type": "error", "error": f"{type(exc).__name__}: {exc}"})
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        while True:
            event = events.get()
            if event is None:
                break
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()


def create_server(port: int = DEFAULT_PORT, portable: bool = True) -> OrganizerServer:
    return OrganizerServer(("127.0.0.1", port), Handler, portable=portable)
