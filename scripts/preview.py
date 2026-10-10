#!/usr/bin/env python3
"""Local NumberInbox site preview (stdlib only, no form endpoint)."""

from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SITE_ROOT = Path(__file__).resolve().parents[1]

def load_rewrites() -> dict[str, str]:
    """Read the exact 200 proxies supported by this site's _redirects file."""
    rewrites = {}
    for line in (SITE_ROOT / "_redirects").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == "200" and not line.lstrip().startswith("#"):
            rewrites.setdefault(parts[0], parts[1])
    return rewrites


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def log_message(self, fmt, *args):  # keep quiet, never log bodies
        sys.stderr.write("preview: " + (fmt % args) + "\n")

    def route_request(self):
        request = urlsplit(self.path)
        path = load_rewrites().get(request.path, request.path)
        # Match Pages' .html canonicalization before serving a proxy target.
        # An incorrect /page -> /page.html proxy will now reproduce the loop.
        if path.endswith(".html") and Path(self.translate_path(path)).is_file():
            canonical = path[:-5]
            if canonical.endswith("/index"):
                canonical = canonical[:-5]
            if request.query:
                canonical += "?" + request.query
            self.send_response(307)
            self.send_header("Location", canonical)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        candidate = Path(self.translate_path(path + ".html"))
        if candidate.is_file():
            path += ".html"
        self.path = path + ("?" + request.query if request.query else "")
        return True

    def do_GET(self):
        if self.route_request():
            return super().do_GET()

    def do_HEAD(self):
        if self.route_request():
            return super().do_HEAD()

    def do_POST(self):
        self.send_error(404)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview the NumberInbox site locally")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port), PreviewHandler
        )
    except OSError as exc:
        print(f"preview: cannot bind 127.0.0.1:{args.port}: {exc}", file=sys.stderr)
        return 1
    print(f"preview: serving {SITE_ROOT} at http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
