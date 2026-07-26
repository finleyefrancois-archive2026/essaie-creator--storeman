"""Local web dashboard server for Smart Organizer."""

from __future__ import annotations

import json
import logging
import queue
import sys
import threading
import time
from collections import defaultdict
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from organizer_core import app_data_dir, execute, save_undo_log, scan, undo

APP_NAME = "Smart File Organizer"
DEFAULT_PORT = 8787

# Configure structured logging
logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

# Allowed base directories for safety (can be extended via config)
ALLOWED_BASE_DIRS: list[Path] = []


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
        # Initialize allowed base directories
        ALLOWED_BASE_DIRS.extend([Path.home(), Path.home() / "Downloads", Path.home() / "Documents"])
        # Rate limiting state
        self.request_times: dict[str, list[float]] = defaultdict(list)
        # Metrics
        self.metrics = {
            "scans_total": 0,
            "files_moved_total": 0,
            "duplicates_detected_total": 0,
            "errors_total": 0,
            "start_time": time.time()
        }


class Handler(BaseHTTPRequestHandler):
    server: OrganizerServer

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        logger.info(format, *args)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

    def _get_client_ip(self) -> str:
        """Extract client IP address for rate limiting."""
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limit. Returns True if allowed."""
        client_ip = self._get_client_ip()
        now = time.time()
        window = RATE_LIMIT_WINDOW_SECONDS
        
        # Clean old entries
        self.server.request_times[client_ip] = [
            t for t in self.server.request_times[client_ip] 
            if now - t < window
        ]
        
        # Check limit
        if len(self.server.request_times[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return False
        
        # Record this request
        self.server.request_times[client_ip].append(now)
        return True

    def _is_safe_path(self, path: Path) -> bool:
        """Validate that path is within allowed directories to prevent path traversal."""
        try:
            resolved = path.resolve()
            # Check against allowed base directories
            for base in ALLOWED_BASE_DIRS:
                try:
                    resolved.relative_to(base.resolve())
                    return True
                except ValueError:
                    continue
            # Also allow the path itself if it's a common user directory
            safe_bases = [Path.home(), Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop"]
            for base in safe_bases:
                try:
                    resolved.relative_to(base.resolve())
                    return True
                except ValueError:
                    continue
            logger.warning(f"Path traversal attempt blocked: {path} -> {resolved}")
            return False
        except (OSError, ValueError) as exc:
            logger.error(f"Path validation error: {exc}")
            return False

    def _validate_plan_item(self, item: Any) -> tuple[bool, str]:
        """Validate a plan item structure. Returns (is_valid, error_message)."""
        if not isinstance(item, dict):
            return False, "Plan item must be a dictionary"
        
        required_fields = {"source", "destination"}
        missing = required_fields - set(item.keys())
        if missing:
            return False, f"Missing required fields: {missing}"
        
        source = Path(item["source"])
        destination = Path(item["destination"])
        
        # Validate paths are absolute
        if not source.is_absolute():
            return False, f"Source path must be absolute: {source}"
        if not destination.is_absolute():
            return False, f"Destination path must be absolute: {destination}"
        
        # Validate no path traversal
        if not self._is_safe_path(source):
            return False, f"Source path outside allowed directories: {source}"
        if not self._is_safe_path(destination):
            return False, f"Destination path outside allowed directories: {destination}"
        
        return True, ""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        
        # Health check endpoint for monitoring
        if parsed.path == "/api/health":
            uptime = time.time() - self.server.metrics["start_time"]
            self._send_json({
                "status": "healthy",
                "uptime_seconds": round(uptime, 2),
                "metrics": self.server.metrics
            })
            return
        
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
            # Check rate limit
            if not self._check_rate_limit():
                self._send_json(
                    {"error": "Rate limit exceeded. Please try again later."},
                    HTTPStatus.TOO_MANY_REQUESTS
                )
                return
            self._scan_stream(parse_qs(parsed.query))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/execute":
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            
            plan = payload.get("plan") or self.server.last_plan
            
            # Validate plan structure
            if not isinstance(plan, list):
                self._send_json({"error": "Plan must be a list of file operations"}, HTTPStatus.BAD_REQUEST)
                return
            
            # Validate each plan item
            for i, item in enumerate(plan):
                is_valid, error_msg = self._validate_plan_item(item)
                if not is_valid:
                    logger.warning(f"Invalid plan item {i}: {error_msg}")
                    self._send_json(
                        {"error": f"Invalid plan item at index {i}: {error_msg}"},
                        HTTPStatus.BAD_REQUEST
                    )
                    return
            
            try:
                result = execute(plan, bool(payload.get("skipDuplicates")))
                save_undo_log(self.server.data_dir, result)
                # Update metrics
                self.server.metrics["files_moved_total"] += len(result.get("moved", []))
                self.server.metrics["errors_total"] += len(result.get("skipped", []))
                self._send_json(result)
            except Exception as exc:
                logger.error(f"Execute failed: {exc}")
                self.server.metrics["errors_total"] += 1
                self._send_json({"error": f"Execution failed: {type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        
        if self.path == "/api/undo":
            try:
                result = undo(self.server.data_dir)
                self._send_json(result)
            except Exception as exc:
                logger.error(f"Undo failed: {exc}")
                self._send_json({"error": f"Undo failed: {type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        
        if self.path == "/api/shutdown":
            self._send_json({"ok": True})
            self.server.shutdown_requested.set()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        
        self.send_error(HTTPStatus.NOT_FOUND)

    def _scan_stream(self, query: dict[str, list[str]]) -> None:
        # Validate source and target paths to prevent path traversal
        try:
            source_list = query.get("source", [str(Path.home() / "Downloads")])
            target_list = query.get("target", [])
            
            source = Path(source_list[0]).expanduser().resolve()
            if target_list:
                target = Path(target_list[0]).expanduser().resolve()
            else:
                target = source / "Organized"
            
            # Security check: validate paths are safe
            if not self._is_safe_path(source):
                self._send_json(
                    {"error": f"Source path not allowed: {source}"},
                    HTTPStatus.FORBIDDEN
                )
                return
            
            if not self._is_safe_path(target):
                self._send_json(
                    {"error": f"Target path not allowed: {target}"},
                    HTTPStatus.FORBIDDEN
                )
                return
                
        except (IndexError, OSError, ValueError) as exc:
            self._send_json(
                {"error": f"Invalid path parameter: {exc}"},
                HTTPStatus.BAD_REQUEST
            )
            return
        
        conflict_mode = query.get("conflict", ["rename"])[0]
        events: queue.Queue[dict | None] = queue.Queue()

        def progress(event: dict) -> None:
            events.put(event)

        def worker() -> None:
            try:
                report = scan(source, target, conflict_mode, progress)
                # Use asdict for consistent serialization
                self.server.last_plan = [asdict(item) for item in report.files if not item.error]
                # Update metrics
                self.server.metrics["scans_total"] += 1
                duplicate_count = sum(1 for item in report.files if item.duplicate)
                self.server.metrics["duplicates_detected_total"] += duplicate_count
            except Exception as exc:  # keep SSE alive for unexpected failures
                logger.error(f"Scan failed: {exc}")
                self.server.metrics["errors_total"] += 1
                events.put({"type": "error", "error": f"{type(exc).__name__}: {exc}"})
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        # Add heartbeat timeout for better connection management
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        
        # Send with timeout and heartbeat support
        while True:
            try:
                event = events.get(timeout=30)
            except queue.Empty:
                # Send heartbeat to keep connection alive
                self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
                continue
            if event is None:
                break
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()


def create_server(port: int = DEFAULT_PORT, portable: bool = True) -> OrganizerServer:
    return OrganizerServer(("127.0.0.1", port), Handler, portable=portable)
