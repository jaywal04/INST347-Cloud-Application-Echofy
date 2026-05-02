#!/usr/bin/env python3
"""Assemble frontend/public/*.html from shared snippets and per-page body fragments.

Run from repo root:
  python scripts/render_static_html.py

Sources:
  frontend/snippets/layout-top.html   (contains {{PAGE_TITLE}})
  frontend/snippets/bodies/<page>.html
  frontend/snippets/footers/<page>.html
"""

from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SNIPPETS = REPO / "frontend" / "snippets"
PUBLIC = REPO / "frontend" / "public"

# (output_filename, page_title, body_stem, footer_stem, defer_script_names without js/)
PAGES: list[tuple[str, str, str, str, list[str]]] = [
    ("index.html", "Echofy", "index", "index", ["main.js", "discover.js"]),
    ("login.html", "Sign In — Echofy", "login", "login", ["auth.js"]),
    ("signup.html", "Sign Up — Echofy", "signup", "signup", ["auth.js"]),
    ("discover.html", "Discover — Echofy", "discover", "discover", ["discover.js"]),
    ("review.html", "Reviews — Echofy", "review", "review", ["reviews-browse.js"]),
    ("friends.html", "Friends — Echofy", "friends", "friends", ["friends.js"]),
    ("profile.html", "Profile — Echofy", "profile", "profile", ["profile.js"]),
    (
        "notifications.html",
        "Notifications — Echofy",
        "notifications",
        "notifications",
        ["notifications.js"],
    ),
    ("user.html", "User Profile — Echofy", "user", "user", ["user-profile.js"]),
]


def render() -> None:
    layout_top = (SNIPPETS / "layout-top.html").read_text(encoding="utf-8")
    if "{{PAGE_TITLE}}" not in layout_top:
        print("layout-top.html must contain {{PAGE_TITLE}}", file=sys.stderr)
        sys.exit(1)

    for out_name, title, body_stem, footer_stem, defer_js in PAGES:
        body_path = SNIPPETS / "bodies" / f"{body_stem}.html"
        footer_path = SNIPPETS / "footers" / f"{footer_stem}.html"
        if not body_path.is_file():
            print(f"Missing body: {body_path}", file=sys.stderr)
            sys.exit(1)
        if not footer_path.is_file():
            print(f"Missing footer: {footer_path}", file=sys.stderr)
            sys.exit(1)

        body = body_path.read_text(encoding="utf-8")
        footer = footer_path.read_text(encoding="utf-8").rstrip() + "\n"
        scripts = "".join(
            f'  <script src="js/{name}" defer></script>\n' for name in defer_js
        )
        top = layout_top.replace("{{PAGE_TITLE}}", title)
        out = top + body + footer + "\n" + scripts + "</body>\n</html>\n"
        dest = PUBLIC / out_name
        dest.write_text(out, encoding="utf-8")
        print("Wrote", dest.relative_to(REPO))


def main() -> None:
    render()


if __name__ == "__main__":
    main()
