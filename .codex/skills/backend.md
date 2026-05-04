# Echofy — backend (Flask)

**When to read this:** App startup, middleware, blueprints, sessions, or CORS.

## Entry point

- Package: `backend/app/`
- WSGI-style app: `app = create_app()` at bottom of `backend/app/main.py` (also used for `python -m` / Azure startup).
- Repo-root `.env` is loaded from `main.py` via `_load_dotenv_compat` (handles UTF-8 and UTF-16 BOM).

## `create_app()` responsibilities (`main.py`)

1. **Flask config**
   - `SECRET_KEY` from `FLASK_SECRET_KEY` (default dev key if unset — change in production).
2. **Session cookies**
   - **Production-like** when any of: `ECHOFY_PRODUCTION` truthy, `FLASK_ENV=production`, or `WEBSITE_HOSTNAME` set (Azure): `SESSION_COOKIE_SAMESITE=None`, `SESSION_COOKIE_SECURE=True`.
   - **Otherwise (local HTTP):** `Lax` + `Secure=False` so sessions work without HTTPS.
   - Always `SESSION_COOKIE_HTTPONLY=True`.
3. **CORS** (`flask_cors`)
   - `supports_credentials=True`, origins from `_echofy_cors_allowed_origins()` (localhost:3001, 127.0.0.1:3001, plus `ECHOFY_SWA_URL`, `ECHOFY_CORS_ORIGINS`, etc.).
   - On Azure, logs a warning if no HTTPS frontend origin is configured.
4. **Database** — `init_db(app)` from `app.database`.
5. **Flask-Login** — `LoginManager`, `user_loader` → `User.query.get`, unauthorized JSON `401`.
6. **Blueprints** (registration order): `telemetry_bp`, `auth_bp`, `friends_bp`, `reviews_bp`.
7. **Error handlers** — `OperationalError` / `DBAPIError` → JSON 503 “temporarily unavailable”.
8. **Routes** — health, config, all `/api/spotify/*`, OAuth `/auth/spotify` and `/callback` (see `api.md`).
9. **Discord** — optional non-blocking startup embed (`_schedule_discord_startup_notification`).

## Module layout

| Module | Role |
|--------|------|
| `main.py` | App factory, Spotify OAuth, Spotify JSON routes, CORS/session |
| `auth.py` | Blueprint `auth`: `/api/auth/*` signup, login, profile, privacy, delete account (also cleans `UserFollow`/`Notification` rows for the deleted user in app code) |
| `friends.py` | Blueprint `friends`: friends list, requests, user search, public profiles, follow/unfollow (`/api/follows/*`), review notifications (`/api/notifications`) |
| `reviews.py` | Blueprint `reviews`, `url_prefix='/api/reviews'`; includes like/reaction endpoints; fires `Notification` rows to followers + friends on new review post |
| `telemetry.py` | Blueprint `telemetry`, `url_prefix='/api/telemetry'` |
| `database.py` | SQLAlchemy `db`, URI build, pool options for remote DB |
| `models.py` | `User`, `PendingVerification`, `FriendRequest`, `SongReview`, `ReviewLike`, `ReviewReaction`, `UserFollow`, `Notification` |
| `schema_sync.py` | Adds missing columns on existing tables; dedupes and adds unique indexes for `review_likes` and `review_reactions`; fixes `review_reactions.emoji` column to `NVARCHAR(32) COLLATE Latin1_General_BIN2` on MSSQL so emoji are stored correctly and compared distinctly |
| `admin/admin_cli.py` | Interactive admin tool: list tables, manage users, reset reactions, diagnose and force-fix the emoji column type/collation |
| `ai_chat.py` | Blueprint `ai_chat`: `GET /api/chat/status` (configured check), `POST /api/chat` (login-required; sends user message + multi-turn history to Azure AI Foundry with top community reviews as context) |
| `spotify_client.py` | HTTP calls to Spotify, token resolution, response shaping |
| `blob_storage.py` | Azure Blob profile images (optional) |
| `email_service.py` | Verification emails |
| `discord_webhook.py` | Embeds for telemetry / startup |
| `envutil.py` | `first_non_empty` for env fallbacks |

## Spotify token plumbing (high level)

- Logged-in users: tokens stored on `User.spotify_access_token` / `spotify_refresh_token` (preferred when resolving API calls).
- Anonymous: tokens in Flask `session`.
- `_persist_spotify_tokens` in `main.py` writes refreshed tokens back to DB or session.

See `spotify_api.md` for OAuth and Web API details.
