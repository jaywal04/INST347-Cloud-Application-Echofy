# Echofy — frontend

**When to read this:** Changing pages, static assets, API calls from the browser, or Static Web Apps behavior.

## Snippets vs `public/`

- **Source of truth for HTML structure:** `frontend/snippets/`
  - `layout-top.html` — opening through `<body>`; must contain `{{PAGE_TITLE}}`.
  - `frontend/snippets/bodies/<page>.html` — main content per page.
  - `frontend/snippets/footers/<page>.html` — closing markup before deferred scripts.
- **Built output:** `frontend/public/*.html` is produced by `scripts/render_static_html.py` (see `PAGES` list in that script).

Do not hand-edit `public/*.html` for structural changes without updating snippets and re-running the render script.

## Pages and scripts (from render script)

Pages listed in `scripts/render_static_html.py` (`PAGES`) are rebuilt by the render script. `posts.html` exists in `frontend/public/` but is **not** in `PAGES` — it is managed separately and must not be hand-edited through snippets.

| Output | Body / footer stems | Deferred JS |
|--------|---------------------|-------------|
| `index.html` | index | `main.js`, `discover.js` |
| `login.html` | login | `auth.js` |
| `signup.html` | signup | `auth.js` |
| `discover.html` | discover | `discover.js` — on load calls `GET /api/spotify/top-tracks` (optional `?view=` from **Chart source**); changing the menu or **Refresh charts** refetches |
| `review.html` | review | `reviews-browse.js` — `GET /api/reviews/browse` (sort/category + optional text `q`); **Search Spotify** → `GET /api/spotify/search` then pick a track → `POST /api/reviews/for-item`; emoji reactions via `POST/DELETE /api/reviews/<id>/reactions` |
| `friends.html` | friends | `friends.js` — friend requests (send/accept/decline), friends list with Remove button (two-step confirm), **Follow/Unfollow** button in search results, **Following** section listing followed users with Unfollow; search calls `GET /api/users/search` (returns `is_following` per result) |
| `profile.html` | profile | `profile.js` |
| `notifications.html` | notifications | `notifications.js` — **Friend requests** section (`GET /api/friends/requests/incoming`, accept/decline); **Activity** section (`GET /api/notifications`) shows `review_posted` notifications from followed users and friends with time-ago labels and unread accent; marks all read on load via `POST /api/notifications/read` |
| `user.html` | user | `user-profile.js` |
| `posts.html` | *(not in render script — managed separately)* | `posts.js` — logged-in **My posts**: `GET /api/reviews`, edit via `POST /api/reviews`, delete via `DELETE /api/reviews/<id>` |

Shared utilities include `navbar.js`, `apiBase.js`, `pathContext.js`, `bugReport.js`, and `chat.js` as referenced by layout/footers. `chat.js` is loaded on **every page** via `layout-top.html` (deferred); it injects the Echo AI side panel into the DOM and wires the `#echofy-ai-nav-btn` button added by `navbar.js` (authenticated users only). Checks `GET /api/chat/status` and `GET /api/auth/me` on first open; supports multi-turn conversation via `POST /api/chat`.

## API base URL (`js/apiBase.js`)

- Sets `window.ECHOFY_API_BASE` and `window.echofyApiBaseUrl()`.
- **Local:** `localhost` / `127.0.0.1` / `::1` map to the API on port **5001** on the same host pattern.
- **Production / non-local:** Loads **`/echofy-config.json`** (same origin) for `{ "apiBase": "https://..." }`. If missing, logs an error (see `echofy-config.example.json`).
- CI writes `echofy-config.json` before SWA deploy from `ECHOFY_BACKEND_URL` (see `deployment.md`).

All authenticated API calls should use `credentials: 'include'` so the Flask session cookie is sent cross-origin when the SPA origin is allowed by CORS.

## Username-prefixed paths (`js/pathContext.js`)

URLs like `/{username}/discover`, `/{username}/posts`, `/{username}/friends`, etc. set:

- `window.ECHOFY_PATH_USERNAME`
- `window.ECHOFY_USER_BASE`
- `window.echofyUserPath(segment)` for links

The script fetches `/api/auth/me` and redirects to `/login` if unauthenticated, or if the logged-in user’s username does not match the path prefix. First path segment must not be reserved (`css`, `js`, `login`, `api`, …).

## Static Web Apps (`frontend/public/staticwebapp.config.json`)

- Explicit rewrites map clean routes (`/login`, `/discover`, `/review`, `/posts`, …) to `*.html`.
- **`navigationFallback`** rewrites unknown paths to `echofy-path-bridge.html` (excludes `/css/*`, `/js/*`, `/.auth/*`, `/echofy-config.json`) so client-side routing / username paths can load the shell.

## Styling and assets

- CSS under `frontend/public/css/` (referenced from layout/snippets).
- No bundler; plain JS and HTML.
