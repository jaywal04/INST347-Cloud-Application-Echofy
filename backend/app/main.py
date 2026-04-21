import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS
from flask_login import LoginManager
from sqlalchemy.exc import DBAPIError, OperationalError

from app.auth import auth_bp
from app.friends import friends_bp
from app.database import init_db
from app.envutil import first_non_empty
from app.models import User
from app.reviews import reviews_bp
from app.spotify_client import (
    SPOTIFY_TOKEN_URL,
    fetch_top_tracks_for_response,
    recommend_tracks_for_genre_response,
    search_spotify_for_response,
)

PORT = int(os.environ.get("PORT", "5001"))

# Load repo-root .env (backend/app/main.py → parents[2] = project root)
_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT / ".env"

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_OAUTH_SCOPE = "user-top-read"


def _load_dotenv_compat(path: Path) -> None:
    if not path.is_file():
        return
    prefix = path.read_bytes()[:4]
    if prefix.startswith(b"\xff\xfe") or prefix.startswith(b"\xfe\xff"):
        load_dotenv(path, encoding="utf-16")
    else:
        load_dotenv(path, encoding="utf-8")


_load_dotenv_compat(_ENV_FILE)


def _spotify_client_id() -> str:
    return first_non_empty("SPOTIFY_CLIENT_ID", "JAY_SPOTIFY_CLIENT_ID")


def _spotify_client_secret() -> str:
    return first_non_empty("SPOTIFY_CLIENT_SECRET", "JAY_SPOTIFY_CLIENT_SECRET")


def _spotify_legacy_user_token() -> str:
    return first_non_empty("SPOTIFY_TOKEN", "JAY_SPOTIFY_TOKEN")


def _strip_env_quotes(value: str) -> str:
    s = (value or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1].strip()
    return s


def _spotify_redirect_uri() -> str:
    raw = first_non_empty("SPOTIFY_REDIRECT_URI", "SPOTIPY_REDIRECT_URI")
    if raw:
        return _strip_env_quotes(raw)
    return "http://127.0.0.1:5001/callback"


def _oauth_success_url() -> str:
    return _strip_env_quotes(
        os.environ.get(
            "ECHOFY_OAUTH_SUCCESS_URL",
            "http://127.0.0.1:3001/discover?spotify=connected",
        )
    )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-echofy-change-me-for-production"
    )
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = not app.debug
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    cors_origins = [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    # Allow the Azure Static Web Apps frontend in production (comma-separated).
    backend_url = os.environ.get("ECHOFY_BACKEND_URL", "").strip()
    for origin in os.environ.get("ECHOFY_SWA_URL", "").split(","):
        origin = origin.strip()
        if not origin:
            continue
        if not origin.startswith("http"):
            origin = "https://" + origin
        cors_origins.append(origin)

    CORS(
        app,
        origins=cors_origins,
        supports_credentials=True,
    )

    # --- Database & Auth ---
    init_db(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify(ok=False, errors=["Login required."]), 401

    app.register_blueprint(auth_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(reviews_bp)

    @app.errorhandler(OperationalError)
    @app.errorhandler(DBAPIError)
    def handle_db_error(error):
        app.logger.error("Database connection error: %s", error)
        return jsonify(ok=False, errors=["Database is temporarily unavailable. Please try again in a moment."]), 503

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/config")
    def api_config():
        url = backend_url
        if url and not url.startswith("http"):
            url = "https://" + url
        return jsonify(backend_url=url or None)

    @app.get("/api/spotify/session")
    def spotify_session():
        return jsonify(
            connected=bool(session.get("spotify_access_token")),
        )

    @app.get("/api/spotify/top-tracks")
    def spotify_top_tracks():
        oauth_tok = session.get("spotify_access_token") or ""
        payload, status = fetch_top_tracks_for_response(
            client_id=_spotify_client_id(),
            client_secret=_spotify_client_secret(),
            legacy_user_token=_spotify_legacy_user_token(),
            oauth_access_token=oauth_tok,
        )
        return jsonify(payload), status

    @app.get("/api/spotify/search")
    def spotify_search():
        oauth_tok = session.get("spotify_access_token") or ""
        payload, status = search_spotify_for_response(
            client_id=_spotify_client_id(),
            client_secret=_spotify_client_secret(),
            legacy_user_token=_spotify_legacy_user_token(),
            oauth_access_token=oauth_tok,
            query=request.args.get("q", ""),
            item_type=request.args.get("type", "track"),
        )
        return jsonify(payload), status

    @app.get("/api/spotify/recommend-by-genre")
    def spotify_recommend_by_genre():
        oauth_tok = session.get("spotify_access_token") or ""
        payload, status = recommend_tracks_for_genre_response(
            client_id=_spotify_client_id(),
            client_secret=_spotify_client_secret(),
            legacy_user_token=_spotify_legacy_user_token(),
            oauth_access_token=oauth_tok,
            genre=request.args.get("genre", ""),
        )
        return jsonify(payload), status

    @app.get("/auth/spotify")
    def spotify_oauth_start():
        client_id = _spotify_client_id()
        redirect_uri = _spotify_redirect_uri()
        if not client_id:
            return jsonify(error="missing_client_id"), 400
        if not redirect_uri:
            return jsonify(
                error="missing_redirect_uri",
                message="Set SPOTIFY_REDIRECT_URI in .env (must match Spotify Dashboard exactly).",
            ), 400

        state = secrets.token_urlsafe(32)
        session["spotify_oauth_state"] = state
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": SPOTIFY_OAUTH_SCOPE,
            "state": state,
        }
        return redirect(f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}")

    @app.get("/callback")
    def spotify_oauth_callback():
        err = request.args.get("error")
        if err:
            return jsonify(error=err, description=request.args.get("error_description", "")), 400

        code = request.args.get("code")
        state = request.args.get("state")
        expected = session.get("spotify_oauth_state")
        session.pop("spotify_oauth_state", None)

        if not code or not state or state != expected:
            return jsonify(error="invalid_state", message="OAuth state mismatch. Try signing in again."), 400

        client_id = _spotify_client_id()
        client_secret = _spotify_client_secret()
        redirect_uri = _spotify_redirect_uri()

        if not client_id or not client_secret:
            return jsonify(error="missing_client_credentials"), 500

        token_res = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=25,
        )

        if token_res.status_code != 200:
            try:
                detail = token_res.json()
            except Exception:
                detail = {"raw": token_res.text[:300]}
            return (
                jsonify(
                    error="token_exchange_failed",
                    status=token_res.status_code,
                    detail=detail,
                ),
                502,
            )

        data = token_res.json()
        access = data.get("access_token")
        if not access:
            return jsonify(error="no_access_token"), 502

        session["spotify_access_token"] = access
        if data.get("refresh_token"):
            session["spotify_refresh_token"] = data["refresh_token"]

        return redirect(_oauth_success_url())

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True, load_dotenv=False)
