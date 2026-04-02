import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from app.spotify_client import fetch_top_tracks_for_response

PORT = int(os.environ.get("PORT", "5000"))

# Load repo-root .env (backend/app/main.py → parents[2] = project root)
_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT / ".env"


def _load_dotenv_compat(path: Path) -> None:
    if not path.is_file():
        return
    prefix = path.read_bytes()[:4]
    if prefix.startswith(b"\xff\xfe") or prefix.startswith(b"\xfe\xff"):
        load_dotenv(path, encoding="utf-16")
    else:
        load_dotenv(path, encoding="utf-8")


_load_dotenv_compat(_ENV_FILE)


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(
        app,
        origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        supports_credentials=True,
    )

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/spotify/top-tracks")
    def spotify_top_tracks():
        token = os.environ.get("JAY_SPOTIFY_TOKEN", "")
        payload, status = fetch_top_tracks_for_response(token)
        return jsonify(payload), status

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)
