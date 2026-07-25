"""Single executable entry point for Smart File Organizer."""

from __future__ import annotations

import argparse
import signal
import threading
import time
import webbrowser

from web_server import DEFAULT_PORT, create_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart File Organizer")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--appdata", action="store_true", help="Store logs in OS app data instead of portable EXE folder")
    args = parser.parse_args()

    server = create_server(args.port, portable=not args.appdata)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://localhost:{args.port}"
    if not args.no_browser:
        webbrowser.open(url)
    print(f"Smart File Organizer is running at {url}")
    print("Close this window or press Ctrl+C to stop.")

    def stop(_signum=None, _frame=None) -> None:
        server.shutdown_requested.set()
        server.shutdown()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while not server.shutdown_requested.is_set():
            time.sleep(0.25)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
