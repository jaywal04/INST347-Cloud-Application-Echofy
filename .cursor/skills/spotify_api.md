# Echofy — Spotify integration

**When to read this:** OAuth flow, token behavior, or anything under `/api/spotify` / `spotify_client.py`.

## Modes of API access

1. **User OAuth (browser)** — User hits `/auth/spotify` → Spotify → `/callback` → access (and refresh) token stored on `User` if logged in, else in Flask `session`.
2. **Client credentials** — If `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` are set, server can obtain an app-only token when no user token is available (chart-style data, search, etc., per Spotify’s rules for those endpoints).
3. **Legacy static user token** — `SPOTIFY_TOKEN` or `JAY_SPOTIFY_TOKEN` env acts like a long-lived user access token for dev/automation (same code paths as OAuth user token where supported).

Resolution logic lives in `spotify_client._resolve_spotify_token` and helpers.

## OAuth details (`main.py`)

- **Authorize URL:** `https://accounts.spotify.com/authorize`
- **Token URL:** `https://accounts.spotify.com/api/token`
- **Scopes:** Default set includes `user-top-read`, `playlist-read-private`, `playlist-read-collaborative`, `user-read-private`, `user-library-read`. Override entirely with env `ECHOFY_SPOTIFY_SCOPES` (space-separated). After scope changes, users must disconnect and reconnect.
- **Redirect URI:** From `SPOTIFY_REDIRECT_URI` / `SPOTIPY_REDIRECT_URI`, or for local requests to localhost/127.0.0.1 auto-built as `http://127.0.0.1:{PORT}/callback` (Spotify often rejects `localhost` — register `127.0.0.1` in the Spotify Dashboard).
- **State:** Random state stored in `_oauth_state_map` with `user_id`, `frontend_host`, `username`, optional `return_origin`. Prevents CSRF; mismatches redirect with `spotify_error=invalid_state`.
- **Post-login redirect:** Uses `return_origin` if valid, else `_oauth_success_url` (env `ECHOFY_OAUTH_SUCCESS_URL` or default discover URL on frontend host).

## Web API usage (`spotify_client.py`)

- Base: `https://api.spotify.com/v1`
- Implements playlist fetch, top tracks, user playlists, search, genre-based recommendations, “recommend like this item”, and chart fallbacks (e.g. Global Top 50 playlist id `37i9dQZEVXbMDoHDwVN2tF`).
- **Search:** Spotify’s API caps `limit` at 10 for `/search`; code uses `_SPOTIFY_SEARCH_MAX_LIMIT = 10`. If a **user** token is used first but Spotify returns **401** (expired), search **retries once** with **client credentials** when ID/secret are set, and may include `spotify_session_note` in the JSON payload.
- Token refresh: refresh token exchanged when access token expires; callback `on_token_refresh` persists new access (and refresh if rotated) to DB or session.

## Market / locale

- Optional `SPOTIFY_MARKET` (ISO country, default US) for playlist/track eligibility where applicable.

## Disconnect

`POST /api/spotify/disconnect` clears DB tokens for the logged-in user and/or session keys.

## Env reference

See `.env.example` for `SPOTIFY_*`, `ECHOFY_OAUTH_SUCCESS_URL`, `ECHOFY_SPOTIFY_SCOPES`, and CORS-related vars used with OAuth return URLs.
