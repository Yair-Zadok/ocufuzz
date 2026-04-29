#!/usr/bin/env python3
# Serves ``test-sites`` on http://127.0.0.1:8765/ for local smoke runs.

from __future__ import annotations

import argparse
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    root = repo / "test-sites"
    if not root.is_dir():
        print(f"Missing folder: {root}", file=sys.stderr)
        sys.exit(1)

    os.chdir(root)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, fmt, *log_args):
            sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % log_args))

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving {root} at http://{args.host}:{args.port}/")
    print("  site-1:  http://%s:%s/site-1/" % (args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
