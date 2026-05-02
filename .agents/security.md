# Echofy — security notes

**When to read this:** Auth bugs, CORS, cookies, OAuth redirects, or handling secrets.

## Passwords and accounts

- Passwords hashed with Werkzeug (`generate_password_hash` / `check_password_hash`) on `User` (`models.py`). Never store plaintext.
- Signup uses email verification codes (`PendingVerification`) before the user row is created.
- Usernames validated with regex; reserved first segments block route collisions (`_RESERVED_USERNAMES` in `auth.py`: `login`, `signup`, `discover`, `api`, `static`, etc.).

## Session cookies

- **HttpOnly** always — mitigates token theft via XSS reading the session cookie.
- **SameSite / Secure:** In production (Azure or `ECHOFY_PRODUCTION` / `FLASK_ENV=production`), cookies use `SameSite=None` and `Secure=True` so cross-site credentialed requests from the SWA origin to the API work over HTTPS.
- On plain HTTP local dev, `Secure=False` and `Lax` — required or the browser will not send the session cookie.

## CORS

- Allowed origins are explicit (`_echofy_cors_allowed_origins` in `main.py`): dev localhost ports, plus `ECHOFY_SWA_URL`, `ECHOFY_CORS_ORIGINS`, `ECHOFY_FRONTEND_ORIGINS`, `ECHOFY_ALLOWED_ORIGINS`, `ECHOFY_FRONTEND_URL`, and origin derived from `ECHOFY_OAUTH_SUCCESS_URL`.
- Credentials supported: browser must send `credentials: 'include'` and origin must match exactly (no wildcard with credentials).

## Spotify OAuth open redirect prevention

- Discover (and similar) may pass `?return=` to `/auth/spotify` with a full frontend URL.
- `_oauth_return_origin_allowed` requires the `return` URL’s `scheme://netloc` to match an entry in the same CORS allowlist — prevents redirecting post-login to arbitrary domains.
- After success, if `return_origin` was stored on the OAuth state, callback redirects to `{origin}/discover?...` or `{origin}/{username}/discovery?...`.

## Spotify and third-party tokens

- **Client ID / secret:** Server env only (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`); never exposed to static frontend.
- **User Spotify tokens:** Stored in DB for logged-in users (`users.spotify_*`); session for anonymous OAuth. Refresh flow persists via `_persist_spotify_tokens`.
- **Legacy static token:** `SPOTIFY_TOKEN` / `JAY_SPOTIFY_TOKEN` — server-side only.

## Discord / telemetry

- Webhook URLs from `DISCORD_WEBHOOK_URL` or `ECHOFY_DISCORD_WEBHOOK_URL` — server only, never sent to clients in responses.
- `POST /api/telemetry/client-error`: no login required (so login failures can report); per-IP sliding window (`_MAX_PER_WINDOW` per `_WINDOW_SEC` in `telemetry.py`) limits abuse.

## Operational hygiene

- Rotate `FLASK_SECRET_KEY` for production.
- Restrict Azure SQL / storage connection strings to deployment secrets, not git.
- Full env catalog: `.env.example` at repo root.
