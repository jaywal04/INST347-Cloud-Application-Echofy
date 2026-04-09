"""Tiny static file server with clean-URL support.

Requests for /discover  →  serves public/discover.html
Requests for /css/styles.css  →  serves public/css/styles.css
Root /  →  serves public/index.html
"""

import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("PORT", "3001"))
DIRECTORY = Path(__file__).resolve().parent / "public"


class CleanURLHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        # Separate path from query string
        if "?" in self.path:
            path, qs = self.path.split("?", 1)
        else:
            path, qs = self.path, ""
        path = path.split("#")[0]

        # If the path has no file extension, try appending .html
        if "." not in path.split("/")[-1] and path != "/":
            html_path = DIRECTORY / path.lstrip("/")
            html_file = html_path.with_suffix(".html")
            if html_file.is_file():
                self.path = path.rstrip("/") + ".html"
                if qs:
                    self.path += "?" + qs

        return super().do_GET()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("", PORT), CleanURLHandler)
    print(f"Frontend at http://localhost:{PORT}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
