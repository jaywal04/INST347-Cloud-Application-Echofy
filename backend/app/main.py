from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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
    recommend_similar_for_item_response,
    recommend_tracks_for_genre_response,
    search_spotify_for_response,
)

PORT = int(os.environ.get("PORT", "5001"))

# Load repo-root .env (backend/app/main.py → parents[2] = project root)
_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT / ".env"

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_OAUTH_SCOPE = "user-top-read"
_spotify_redirect_port_warning_shown = False


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
    """
    Must match Spotify Dashboard and this server's PORT. Many clones still have
    SPOTIFY_REDIRECT_URI=...:5000 in .env while the app listens on 5001 — Spotify
    would then send the browser to a dead port. For localhost / 127.0.0.1 we align
    the callback port to PORT automatically.
    """
    global _spotify_redirect_port_warning_shown
    listen_port = int(os.environ.get("PORT", str(PORT)))
    raw = first_non_empty("SPOTIFY_REDIRECT_URI", "SPOTIPY_REDIRECT_URI")
    if not raw:
        return f"http://localhost:{listen_port}/callback"
    uri = _strip_env_quotes(raw)
    parsed = urlparse(uri)
    host = (parsed.hostname or "").lower()
    if host not in ("127.0.0.1", "localhost"):
        return uri
    if parsed.port == listen_port:
        return uri
    scheme = parsed.scheme or "http"
    hn = parsed.hostname or "localhost"
    netloc = f"{hn}:{listen_port}"
    path = parsed.path or "/callback"
    fixed = urlunparse((scheme, netloc, path, "", "", ""))
    if not _spotify_redirect_port_warning_shown:
        _spotify_redirect_port_warning_shown = True
        print(
            "[echofy] SPOTIFY_REDIRECT_URI port does not match this server PORT="
            f"{listen_port}. Using {fixed} for Spotify OAuth. Add that exact URI in the "
            "Spotify Developer Dashboard (and set SPOTIFY_REDIRECT_URI in .env to match).",
            file=sys.stderr,
        )
    return fixed


def _oauth_success_url() -> str:
    return _strip_env_quotes(
        os.environ.get(
            "ECHOFY_OAUTH_SUCCESS_URL",
            "http://localhost:3001/discover?spotify=connected",
        )
    )


def _discover_redirect_url(**query_updates: str) -> str:
    """Build Discover URL using same scheme/host/path as ECHOFY_OAUTH_SUCCESS_URL."""
    p = urlparse(_oauth_success_url())
    path = (p.path or "/discover").split("?")[0] or "/discover"
    merged = dict(parse_qsl(p.query, keep_blank_values=True))
    for key, value in query_updates.items():
        if value:
            merged[key] = value
        else:
            merged.pop(key, None)
    if "spotify_error" in query_updates:
        merged.pop("spotify", None)
    q = urlencode(merged)
    return urlunparse((p.scheme, p.netloc, path, "", q, ""))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-echofy-change-me-for-production"
    )
    # Local dev is HTTP. Secure=True + SameSite=None breaks the session cookie in the
    # browser (no cookie → Spotify OAuth tokens never stick). Cross-origin SWA + API
    # on HTTPS needs None + Secure — production: ECHOFY_PRODUCTION=1, FLASK_ENV=production,
    # or Azure App Service (WEBSITE_HOSTNAME is always set there).
    _prod_session = (
        os.environ.get("ECHOFY_PRODUCTION", "").strip().lower() in ("1", "true", "yes")
        or os.environ.get("FLASK_ENV", "").strip().lower() == "production"
        or bool(os.environ.get("WEBSITE_HOSTNAME", "").strip())
    )
    if _prod_session:
        app.config["SESSION_COOKIE_SAMESITE"] = "None"
        app.config["SESSION_COOKIE_SECURE"] = True
    else:
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["SESSION_COOKIE_SECURE"] = False
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

    @app.post("/api/spotify/disconnect")
    def spotify_disconnect():
        session.pop("spotify_access_token", None)
        session.pop("spotify_refresh_token", None)
        session.pop("spotify_oauth_state", None)
        return jsonify(ok=True, connected=False)

    def _persist_spotify_session_tokens(access: str, new_refresh: str | None) -> None:
        session["spotify_access_token"] = access
        if new_refresh:
            session["spotify_refresh_token"] = new_refresh

    @app.get("/api/spotify/top-tracks")
    def spotify_top_tracks():
        oauth_tok = session.get("spotify_access_token") or ""
        refresh_tok = session.get("spotify_refresh_token") or ""
        payload, status = fetch_top_tracks_for_response(
            client_id=_spotify_client_id(),
            client_secret=_spotify_client_secret(),
            legacy_user_token=_spotify_legacy_user_token(),
            oauth_access_token=oauth_tok,
            oauth_refresh_token=refresh_tok,
            on_token_refresh=_persist_spotify_session_tokens,
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

    @app.post("/api/spotify/recommend-like")
    def spotify_recommend_like():
        oauth_tok = session.get("spotify_access_token") or ""
        payload, status = recommend_similar_for_item_response(
            client_id=_spotify_client_id(),
            client_secret=_spotify_client_secret(),
            legacy_user_token=_spotify_legacy_user_token(),
            oauth_access_token=oauth_tok,
            item=request.get_json(silent=True) or {},
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
            desc = (request.args.get("error_description") or "").strip()
            return redirect(
                _discover_redirect_url(spotify_error=err, spotify_error_description=desc)
            )

        code = request.args.get("code")
        state = request.args.get("state")
        expected = session.get("spotify_oauth_state")
        session.pop("spotify_oauth_state", None)

        if not code or not state or state != expected:
            return redirect(
                _discover_redirect_url(
                    spotify_error="invalid_state",
                    spotify_error_description="OAuth state mismatch. Close this tab and use Connect Spotify again.",
                )
            )

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
