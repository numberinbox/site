#!/usr/bin/env python3
"""Local NumberInbox site preview (stdlib only, no form endpoint)."""

from __future__ import annotations

import argparse
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SITE_ROOT = Path(__file__).resolve().parents[1]

REWRITES = {
    "/privacy": "/index.html",
    "/delete-account": "/delete-account.html",
}


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def log_message(self, fmt, *args):  # keep quiet, never log bodies
        sys.stderr.write("preview: " + (fmt % args) + "\n")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in REWRITES:
            self.path = REWRITES[path]
        return super().do_GET()

    def do_POST(self):
        self.send_error(404)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview the NumberInbox site locally")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port), partial(PreviewHandler)
        )
    except OSError as exc:
        print(f"preview: cannot bind 127.0.0.1:{args.port}: {exc}", file=sys.stderr)
        return 1
    print(f"preview: serving {SITE_ROOT} at http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
