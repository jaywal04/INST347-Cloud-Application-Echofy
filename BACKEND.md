# Echofy — Backend Technical Summary

## What It Is

Echofy is a music community platform where users rate and review songs, albums, artists, and genres sourced from Spotify. The backend is a Python/Flask REST API that handles authentication, user data, Spotify integration, AI chat, and real-time community stats. It runs on **Azure App Service** and is consumed by a static frontend hosted on **Azure Static Web Apps**.

---

## Cloud Requirements Satisfied

### 3.1 Compute — Azure App Service
The Flask API is deployed on **Azure App Service (Python 3.12)**. All application logic lives here: authentication, session management, database queries, Spotify OAuth, AI chat, and telemetry. This is not a static site — every meaningful user action goes through the API.

- Entry point: `backend/app/main.py` → `create_app()`
- Start command: `backend/startup.sh` (sets `PORT`, runs `gunicorn`)
- CI/CD deploys on every push to `main` via GitHub Actions (`.github/workflows/main_echofy-backend.yml`)

### 3.2 Database — Azure SQL (Microsoft SQL Server)
All application data is stored in **Azure SQL**. The connection string is passed via `AZURE_SQL_CONNECTION_STRING`; the app falls back to a local SQLite file for development. SQLAlchemy handles the ORM and query layer.

Tables and their purpose:

| Table | What it stores |
|---|---|
| `users` | Credentials, profile data, privacy settings, Spotify tokens |
| `pending_verifications` | Email verification codes for signup and account deletion |
| `friend_requests` | Directed friend requests + accepted friendships |
| `song_reviews` | User ratings and written reviews for Spotify items |
| `review_likes` | Community likes on reviews |
| `review_reactions` | Emoji reactions on reviews |
| `user_follows` | One-way follow relationships |
| `notifications` | Activity notifications for followers and friends |

Schema is managed automatically: `db.create_all()` creates new tables on startup, and `schema_sync.py` runs `ALTER TABLE` migrations for existing databases — no manual migration scripts needed.

### 3.3 Object Storage — Azure Blob Storage
Profile photos are stored in **Azure Blob Storage** (`AZURE_STORAGE_CONNECTION_STRING`, container `echofy-profiles`). When a user uploads a profile photo:
1. The binary is sent to `POST /api/auth/profile/photo`
2. The Flask backend uploads it to Blob via `blob_storage.py`
3. The returned URL is saved on the `users` row and served directly to the frontend

Deleting an account removes the blob as well. This is a real use case with real user-uploaded images, not a placeholder.

### 3.4 User Interface — Static Web App + Vanilla JS
The frontend is a multi-page static site (HTML + vanilla JS, no framework) deployed to **Azure Static Web Apps**. It communicates with the Flask API over HTTPS using `fetch()` with `credentials: 'include'` for session cookies.

Key pages: Home, Discover (Spotify charts/search), Review browser, My Posts, Friends, Profile, Notifications, User profiles.

A CI step (`scripts/render_static_html.py`) assembles final HTML pages from shared layout snippets before each deploy, so layout changes only need to be made in one place.

### 3.5 GitHub
All code is tracked at: **[github.com/jaywal04/INST347-Cloud-Application-Echofy](https://github.com/jaywal04/INST347-Cloud-Application-Echofy)**

The repository includes a `README.md` with setup instructions. Commit history reflects ongoing development across features: auth, Spotify integration, reviews, friends/follows, AI chat, notifications, schema migrations, and bug fixes.

### 3.6 Automation — GitHub Actions CI/CD
Two GitHub Actions workflows run on every push to `main`:

**Backend workflow** (`.github/workflows/main_echofy-backend.yml`):
- Installs `requirements.txt`
- Smoke-tests the app import (`from app.main import app`)
- Stages `backend/app/`, `requirements.txt`, and `startup.sh`
- Deploys to Azure App Service via publish profile secret

**Frontend workflow** (`.github/workflows/azure-static-web-apps-*.yml`):
- Reads `ECHOFY_BACKEND_URL` secret and writes `frontend/public/echofy-config.json` so the JS knows the API URL at runtime
- Runs `python scripts/render_static_html.py` to assemble all HTML pages from snippets
- Deploys `frontend/public/` to Azure Static Web Apps

No manual steps are needed to ship a change — commit to `main` and both services are updated automatically.

### 3.7 AI Usage
**Echo AI** is an in-app AI chat assistant powered by **Azure AI Foundry (GPT-4o)**. It is accessible from every page via a side panel in the navbar. On each request it uses a RAG (retrieval-augmented generation) pattern: the top 25 community reviews (ranked by likes and rating) are injected as context into the system prompt, so Echo can answer questions like "what music is trending?" or "what should I listen to?" based on real Echofy data.

**AI tools used during development:** Claude Code (Anthropic) was used throughout the project for code generation, debugging, schema design, and documentation.

---

## Backend Architecture

### App Factory Pattern

`create_app()` in `main.py` wires everything together:

1. Flask config (secret key, session cookies)
2. Session cookie settings — `SameSite=None; Secure` in production (Azure), `Lax; Secure=False` locally
3. CORS — explicit origin allowlist (`ECHOFY_SWA_URL`, `ECHOFY_CORS_ORIGINS`, localhost ports)
4. Database init (`init_db`) — SQLAlchemy + `schema_sync`
5. Flask-Login (`LoginManager`, `user_loader`)
6. Blueprint registration: `telemetry_bp`, `auth_bp`, `friends_bp`, `reviews_bp`, `ai_chat_bp`
7. Error handlers — DB errors → JSON 503; unhandled exceptions → JSON 500
8. Core routes: health, config, stats, all Spotify endpoints, OAuth flow
9. Optional Discord startup notification

### Blueprints

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `auth_bp` | — | Signup (email verify), login, logout, session check, profile, photo upload, account deletion |
| `friends_bp` | — | Friend requests, user search, public profiles, follow/unfollow, notifications |
| `reviews_bp` | `/api/reviews` | Create/edit/delete reviews, public browse, reactions, likes |
| `ai_chat_bp` | — | `GET /api/chat/status`, `POST /api/chat` — Azure AI Foundry integration |
| `telemetry_bp` | `/api/telemetry` | Client error reporting → Discord webhook |

### File Structure

```
backend/
├── app/
│   ├── main.py           # App factory, Spotify routes, OAuth, core routes
│   ├── auth.py           # Auth blueprint
│   ├── friends.py        # Friends/follows/notifications blueprint
│   ├── reviews.py        # Reviews blueprint
│   ├── ai_chat.py        # Echo AI blueprint
│   ├── telemetry.py      # Telemetry blueprint
│   ├── models.py         # SQLAlchemy models
│   ├── database.py       # URI selection, engine options, init_db
│   ├── schema_sync.py    # Startup ALTER TABLE migrations
│   ├── spotify_client.py # Spotify Web API helpers, token refresh, response shaping
│   ├── blob_storage.py   # Azure Blob profile photo upload/delete
│   ├── email_service.py  # Resend SDK — verification emails
│   ├── discord_webhook.py# Startup ping + client error embeds
│   ├── envutil.py        # first_non_empty() for env var fallbacks
│   └── admin/
│       └── admin_cli.py  # Interactive DB admin tool (list/view/delete users, diagnose schema)
├── startup.sh            # Gunicorn start command for App Service
└── instance/
    └── echofy.db         # SQLite fallback (local dev only, gitignored)
```

---

## Key Flows

### Authentication
1. User submits email + username + password to `POST /api/auth/signup`
2. Backend creates a `PendingVerification` row and sends a 6-digit code via **Resend** email
3. User submits code to `POST /api/auth/verify-signup` — on success the `User` row is created
4. `POST /api/auth/login` checks password hash (Werkzeug) and calls `login_user()` — Flask sets an HttpOnly session cookie
5. All subsequent requests include the cookie; Flask-Login loads the user via `user_loader`

### Spotify OAuth
1. Frontend redirects to `GET /auth/spotify` — backend stores a random state token and redirects to Spotify's authorize URL
2. Spotify redirects to `GET /callback` with an authorization code
3. Backend exchanges the code for access + refresh tokens (server-side only) and saves them to the `users` row (or session for anonymous)
4. On every Spotify API call, the backend automatically refreshes expired tokens and persists the new ones

### Review Flow
1. User picks a track from Spotify search or top charts and submits a rating (1–5 stars) + optional text
2. `POST /api/reviews` upserts a `SongReview` row (unique per user + item hash)
3. On new reviews (not edits), `_notify_followers_and_friends` creates `Notification` rows for all followers and accepted friends
4. Public endpoints (`/api/reviews/browse`, `/api/reviews/recent`) serve reviews with like counts and reaction emoji aggregates

### Account Deletion
1. User requests deletion — backend sends a verification code via email
2. On code confirmation, before deleting the `User` row:
   - Reviews are **kept** — `user_id` set to NULL, `display_username` set to `"[deleted]"`
   - Friend requests, likes, reactions, incoming follows, actor notifications are deleted
3. User row is deleted; Blob profile photo is removed

### Echo AI Chat
1. Frontend `POST /api/chat` with message + conversation history
2. Backend fetches top 25 reviews (by likes + rating) from the DB as RAG context
3. Message + history + context are sent to Azure AI Foundry (GPT-4o)
4. Reply is streamed back and rendered as Markdown in the side panel

---

## External Services

| Service | Purpose | Env var(s) |
|---|---|---|
| Azure App Service | Hosts the Flask API | (platform-managed) |
| Azure SQL | Primary database | `AZURE_SQL_CONNECTION_STRING` |
| Azure Blob Storage | Profile photo storage | `AZURE_STORAGE_CONNECTION_STRING` |
| Azure AI Foundry | Echo AI (GPT-4o) | `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_KEY`, `AZURE_AI_FOUNDRY_MODEL` |
| Spotify Web API | Music data, OAuth, charts | `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` |
| Resend | Transactional email | `RESEND_API_KEY` |
| Discord | Startup ping + error alerts | `DISCORD_WEBHOOK_URL` |

---

## Security Highlights

- Passwords hashed with Werkzeug (`pbkdf2:sha256`) — plaintext never stored or logged
- Session cookies are `HttpOnly` always; `SameSite=None; Secure` in production for cross-origin SWA→API calls
- Spotify client ID/secret never sent to the frontend — all OAuth happens server-side
- CORS allowlist is explicit — no wildcard with credentials
- Spotify OAuth state token validated on callback to prevent open-redirect attacks
- Client error telemetry sanitizes payloads to remove any strings matching secret/token/password patterns before forwarding to Discord
- Rate limiting on the telemetry endpoint (per-IP sliding window)
