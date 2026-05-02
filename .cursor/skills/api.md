# Echofy — HTTP API reference

**When to read this:** Implementing or debugging a specific endpoint or client fetch.

Conventions: JSON bodies for POST/PUT unless noted. Auth uses Flask session cookies (`credentials: 'include'` from the browser).

---

## Core

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | `{ "status": "ok" }` |
| GET | `/api/config` | No | `{ "backend_url": "<ECHOFY_BACKEND_URL or null>" }` — optional hint for clients |

---

## Spotify (implemented in `main.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/spotify/session` | Session optional | `{ "connected": bool }` — user tokens in DB or session |
| GET | `/api/spotify/playlists` | OAuth/session | User playlists (requires user token + refresh) |
| GET | `/api/spotify/playlists/<playlist_id>/tracks` | OAuth/session | Tracks in a playlist |
| POST | `/api/spotify/disconnect` | Session optional | Clears Spotify tokens (DB if logged in, else session) |
| GET | `/api/spotify/top-tracks` | Optional user/OAuth | Top tracks or fallbacks (client credentials / chart) |
| GET | `/api/spotify/search` | Optional | Query params `q`, `type` (e.g. track) |
| GET | `/api/spotify/recommend-by-genre` | Optional | Query param `genre` |
| POST | `/api/spotify/recommend-like` | Optional | JSON body `item` for similarity recommendations |
| GET | `/auth/spotify` | Session optional | Redirects to Spotify authorize URL; query `return=` must be allowlisted origin |
| GET | `/callback` | — | Spotify OAuth redirect; exchanges code, stores tokens, redirects to frontend |

---

## Auth (`auth.py` — blueprint without URL prefix)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/signup` | No | Start signup (email verification flow) |
| POST | `/api/auth/verify-signup` | No | Verify code and create user |
| POST | `/api/auth/resend-code` | No | Resend verification |
| POST | `/api/auth/login` | No | Login |
| POST | `/api/auth/logout` | Yes | Logout |
| GET | `/api/auth/me` | No | `{ authenticated, user? }` |
| GET | `/api/auth/profile` | Yes | Full profile |
| PUT | `/api/auth/profile` | Yes | Update profile fields |
| POST | `/api/auth/profile/photo` | Yes | Upload profile image (Blob if configured) |
| DELETE | `/api/auth/profile/photo` | Yes | Remove photo |
| PUT | `/api/auth/privacy` | Yes | Privacy toggles |
| POST | `/api/auth/delete-request` | Yes | Start account deletion verification |
| DELETE | `/api/auth/account` | Yes | Complete deletion after verification |

---

## Friends & users (`friends.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users/<int:user_id>/profile` | Yes | Public profile view (respects privacy) |
| GET | `/api/users/search` | Yes | Search users (excludes pending/accepted connections) |
| GET | `/api/friends` | Yes | Friends list |
| GET | `/api/notifications/count` | Yes | Notification badge count |
| GET | `/api/friends/requests/incoming` | Yes | Incoming friend requests |
| GET | `/api/friends/requests/outgoing` | Yes | Outgoing friend requests |
| POST | `/api/friends/requests` | Yes | Send friend request (JSON with target user id) |
| POST | `/api/friends/requests/<int:request_id>/accept` | Yes | Accept |
| POST | `/api/friends/requests/<int:request_id>/decline` | Yes | Decline |

---

## Reviews (`reviews.py` — prefix `/api/reviews`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reviews/recent` | No | Recent reviews feed (for landing); each review includes `username`, `user_id`, `like_count`, `liked_by_me`, `reaction_counts` (emoji→count; **key order** = first time that emoji appeared on the review, stable when counts change), `my_reactions` (session-aware) |
| GET | `/api/reviews/browse` | No | Public browse: `sort` (`top` = most **community likes** then star rating, default; also `recent`, `oldest`, `least`), `category` (`all` default, `tracks`, `albums`, `artists`, `genres`), optional `q` or `search` (substring on title, artists, album, review text; max 120 chars), `limit` (default 50, max 100), `offset`; each row includes `username`, `user_id`, `like_count`, `liked_by_me`, `reaction_counts` (emoji→count; **key order** = first appearance on that review), `my_reactions` |
| POST | `/api/reviews/for-item` | No | Public read: JSON `{ "item": { ... } }` — Spotify **track** only (`type` track, `name`, `url` open.spotify.com/track or spotify:track:); returns `reviews` ordered by likes then rating (same hash as Discover), `item_key`, `item` echo; reviews include `like_count` / `liked_by_me` / `reaction_counts` (same stable key order) / `my_reactions` |
| GET | `/api/reviews/reactions/allowed` | No | `{ ok, emojis: [...] }` — fixed allowlist of emoji strings clients may send for reactions |
| POST | `/api/reviews/<int:review_id>/reactions` | Yes | JSON `{ "emoji": "<allowlisted>" }` — add your reaction; idempotent if duplicate; returns `reaction_counts`, `my_reactions` |
| DELETE | `/api/reviews/<int:review_id>/reactions` | Yes | JSON `{ "emoji": "<allowlisted>" }` — remove your reaction; returns `reaction_counts`, `my_reactions` |
| POST | `/api/reviews/<int:review_id>/like` | Yes | Like a review (not your own); idempotent if already liked; returns `like_count`, `liked_by_me` |
| DELETE | `/api/reviews/<int:review_id>/like` | Yes | Remove your like; returns `like_count`, `liked_by_me` |
| GET | `/api/reviews` | Yes | Current user’s reviews (up to 200) |
| POST | `/api/reviews` | Yes | Create or update review (JSON `item`, `rating`, optional `text`, `item_key`) |

---

## Telemetry (`telemetry.py` — prefix `/api/telemetry`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/telemetry/client-error` | No | Sanitized client errors → optional Discord; IP rate limited |

---

## Errors

- DB connectivity: `503` with generic message from global handler.
- Login required: `401` from Flask-Login `unauthorized_handler`.
- Per-route validation returns `4xx` with `ok: false` and `errors` array where applicable.
