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

| Output | Body / footer stems | Deferred JS |
|--------|---------------------|-------------|
| `index.html` | index | `main.js`, `discover.js` |
| `login.html` | login | `auth.js` |
| `signup.html` | signup | `auth.js` |
| `discover.html` | discover | `discover.js` — on load calls `GET /api/spotify/top-tracks` (optional `?view=` from **Chart source**); changing the menu or **Refresh charts** refetches |
| `review.html` | review | `reviews-browse.js` — `GET /api/reviews/browse` (sort/category + optional text `q`); **Search Spotify** → `GET /api/spotify/search` then pick a track → `POST /api/reviews/for-item`; empty track reviews CTA links to `/discover` |
| `posts.html` | posts | `posts.js` — logged-in **My posts**: `GET /api/reviews`, edit via `POST /api/reviews`, delete via `DELETE /api/reviews/<id>`; nav link **My posts** (`/{username}/posts` when prefixed) |
| `friends.html` | friends | `friends.js` |
| `profile.html` | profile | `profile.js` |
| `notifications.html` | notifications | `notifications.js` |
| `user.html` | user | `user-profile.js` |

Shared utilities include `navbar.js`, `apiBase.js`, `pathContext.js`, `bugReport.js` as referenced by layout/footers.

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
