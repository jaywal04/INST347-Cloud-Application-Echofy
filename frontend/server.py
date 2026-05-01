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

# /{username}/dashboard → discover.html (same for discover)
_USER_PAGE_HTML = {
    "dashboard": "discover.html",
    "discover": "discover.html",
    "friends": "friends.html",
    "profile": "profile.html",
    "notifications": "notifications.html",
    "user": "user.html",
}
_STATIC_FIRST_SEGMENTS = frozenset({"css", "js", "assets", "fonts"})


class CleanURLHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def handle(self):
        # Client closed the socket before a full request (common on Windows / browsers).
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        # Separate path from query string
        if "?" in self.path:
            path, qs = self.path.split("?", 1)
        else:
            path, qs = self.path, ""
        path = path.split("#")[0]

        segments = [s for s in path.split("/") if s]
        if len(segments) >= 2:
            first, page = segments[0], segments[1]
            if (
                first.lower() not in _STATIC_FIRST_SEGMENTS
                and page in _USER_PAGE_HTML
            ):
                inner = _USER_PAGE_HTML[page]
                self.path = "/" + inner + ("?" + qs if qs else "")
                return super().do_GET()

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
