## Project layout

| Path | Purpose |
|------|---------|
| `frontend/public/` | Built static site (served locally and deployed to Azure Static Web Apps) |
| `frontend/snippets/` | Shared HTML layout, per-page body fragments, and footers — run `python scripts/render_static_html.py` to regenerate `public/*.html` |
| `scripts/` | `render_static_html.py`, optional `admin_cli.py`, and `prototypes/` course scripts |
| `backend/app/` | Backend application package (API, services, auth, database) |
| `Dockerfile` | Optional container image for Azure Container Apps (App Service uses GitHub Actions + `backend/startup.sh`) |

The cosine-similarity prototype script lives at [`scripts/prototypes/echofy_model_prototype.py`](scripts/prototypes/echofy_model_prototype.py) (run with `python scripts/prototypes/echofy_model_prototype.py`). After editing HTML snippets, run **`python scripts/render_static_html.py`** from the repo root before committing changes to pages under `frontend/public/`. CI runs the same step before each Static Web Apps deploy.

### Key frontend pages

| Page | Purpose |
|------|---------|
| `index.html` | Landing page with trending albums, recent reviews, and stats |
| `discover.html` | Spotify integration — connect your account and browse top tracks |
| `signup.html` | Create a new account (email, username, password with strength indicator, terms) |
| `login.html` | Sign in with username and password |

### Key backend modules

| Module | Purpose |
|--------|---------|
| `app/main.py` | Flask app factory, Spotify OAuth routes, CORS, session config |
| `app/auth.py` | Auth API routes — signup, login, logout, session check (`/api/auth/*`) |
| `app/models.py` | SQLAlchemy User model (hashed passwords, email, username, terms) |
| `app/database.py` | Database config — SQLite locally, Azure SQL when credentials are provided |
| `app/schema_sync.py` | On startup, adds missing `users` columns to match the model (Azure SQL / SQLite) |
| `app/blob_storage.py` | Azure Blob uploads for profile photos when `AZURE_STORAGE_CONNECTION_STRING` is set |
| `app/spotify_client.py` | Spotify Web API helpers (client credentials, user tokens, track normalization) |

<hr>

## Quick start

### 1. Set up the virtual environment

Create a virtual environment in the project root so dependencies stay isolated. The `.venv` folder is gitignored.

**Windows (PowerShell or Command Prompt):**

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `python` is not found, try `py -3` instead of `python`. To leave the environment: `deactivate`

**macOS / Linux (Terminal):**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

To leave the environment: `deactivate`

### 2. Configure environment variables

Copy `.env.example` to `.env` in the repo root and fill in your values. See the [Environment variables](#environment-variables) section below for details.

### 3. Run the app

| Service | Port | How to run |
|---------|------|------------|
| Both at once | **3001** + **5001** | `start.bat` (Windows) or `./start.sh` (macOS / Linux) opens two terminal windows |
| Frontend only | **3001** | `start.bat frontend` or `./start.sh frontend` (optional: `PORT=8080 ./start.sh frontend`) |
| Backend only | **5001** | `start.bat backend` or `./start.sh backend` (optional: `PORT=5001 ./start.sh backend`) |

Check the API with [http://127.0.0.1:5001/api/health](http://127.0.0.1:5001/api/health).

**macOS note:** Run `./start.sh` from the Terminal app. Double-clicking the file in Finder will open it in a text editor. If you get a “permission denied” error, run `chmod +x start.sh` first.

**Linux note:** `./start.sh` needs a supported terminal emulator (GNOME Terminal, Konsole, XFCE Terminal, or xterm).

<hr>

## User accounts

Echofy has a built-in account system. Users can sign up and log in from the navigation bar.

- **Sign up** (`signup.html`): asks for email, username, and password. Includes a real-time password strength indicator (weak / fair / good / strong), a confirm-password field with match checking, and a required Terms of Service checkbox.
- **Log in** (`login.html`): asks for username and password only.
- Passwords are hashed server-side with Werkzeug (never stored in plain text).

### Auth API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/signup` | Create a new account. Body: `{ email, username, password, confirmPassword, acceptedTerms }` |
| `POST` | `/api/auth/login` | Sign in. Body: `{ username, password }` |
| `POST` | `/api/auth/logout` | Sign out (requires active session) |
| `GET` | `/api/auth/me` | Check current session (returns `{ authenticated, user }` including optional `profile_image_url`) |
| `GET` | `/api/auth/profile` | Full profile for the logged-in user (requires session) |
| `PUT` | `/api/auth/profile` | Update profile fields (`age`, `sex` or `gender`, `bio`, etc.) |
| `POST` | `/api/auth/profile/photo` | Upload profile image — `multipart/form-data` field `file` (JPEG/PNG/WebP, max 5 MB); requires Azure Blob config |
| `DELETE` | `/api/auth/profile/photo` | Remove profile photo from storage and clear URL |

### Database

By default, the backend uses **SQLite** (`backend/instance/echofy.db`) — no setup required, the database file is created automatically on first run. The path is absolute so the same database is used regardless of which directory you start the server from.

To use **Azure SQL** in production, set `AZURE_SQL_CONNECTION_STRING` in `env`:

```
AZURE_SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=tcp:yourserver.database.windows.net,1433;Database=echofy-relational-db;Uid=admin;Pwd=yourpassword;Encrypt=yes;TrustServerCertificate=no;
```

The app switches automatically — no code changes needed. You can also set `DATABASE_URL` for any other SQLAlchemy-compatible database (PostgreSQL, MySQL, etc.).

**Schema updates:** On startup, after `create_all()`, the app compares the `users` table to the SQLAlchemy `User` model and runs `ALTER TABLE ... ADD` for any **missing** columns (for **SQLite** and **Microsoft SQL Server / Azure SQL** only). That way an older Azure `users` table gains fields such as `age`, `sex`, `bio`, `profile_image_url`, and privacy flags without a manual migration. Other databases are unchanged by this step.

### Profile pictures (Azure Blob Storage)

1. Create a **Storage account** and a **container** in [Azure Portal](https://portal.azure.com) (or CLI).
2. Copy the storage account **connection string** into **`AZURE_STORAGE_CONNECTION_STRING`** in `.env` (or App Service application settings).
3. Optionally set `AZURE_STORAGE_CONTAINER_PROFILES` (default echofy-profiles).. The app creates the container on first upload with **blob-level public read** so the stored HTTPS URL works in `<img src="...">`.
4. Without a connection string, photo upload returns an error; the rest of the app still runs.

<hr>

## Spotify (Discover page)

1. In the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), add a **Redirect URI** that matches **`SPOTIFY_REDIRECT_URI`** in your `.env` (default `http://127.0.0.1:5001/callback`). Spotify often rejects `localhost`; **`127.0.0.1`** is fine.
2. Set **`SPOTIFY_CLIENT_ID`** and **`SPOTIFY_CLIENT_SECRET`** in repo-root `.env` (see [`.env.example`](.env.example)). Older **`JAY_SPOTIFY_*`** names are still read if the `SPOTIFY_*` variables are empty.
3. **Connect Spotify** on the Discover page (or open `http://127.0.0.1:5001/auth/spotify`) to sign in; after callback, **your top tracks** are used when you click “Show top Spotify music,” with chart fallbacks when needed.
4. Without a connected session, **Client Credentials** loads chart-style data (Top 50 if allowed, else new releases / featured playlists) when ID and secret are set.
5. For local OAuth, use the frontend at **`http://localhost:3001`** or **`http://127.0.0.1:3001`**; the static `js/apiBase.js` points API calls at **`http://127.0.0.1:5001`** or **`http://localhost:5001`** as appropriate.
6. Optional **`SPOTIFY_TOKEN`**: same behavior as a connected user token without the browser flow (legacy **`JAY_SPOTIFY_TOKEN`** if `SPOTIFY_TOKEN` is empty).

<hr>

## Environment variables

All variables go in a `.env` file at the repo root. The static frontend does **not** read `.env`; it only calls the API.

| Variable | Purpose |
|----------|---------|
| `PORT` | Flask port (default `5001` in code; Azure App Service sets this automatically). |
| `FLASK_SECRET_KEY` | Signs session cookies; change for production. |
| **Spotify** | |
| `SPOTIFY_CLIENT_ID` | Spotify Client ID (`JAY_SPOTIFY_CLIENT_ID` if empty). |
| `SPOTIFY_CLIENT_SECRET` | Spotify Client Secret (`JAY_SPOTIFY_CLIENT_SECRET` if empty). |
| `SPOTIFY_TOKEN` | Optional static user access token (`JAY_SPOTIFY_TOKEN` if empty). |
| `SPOTIFY_MARKET` | Optional ISO market for playlist requests (default `US`). |
| `SPOTIFY_REDIRECT_URI` | OAuth callback URL (must match Dashboard). Legacy: `SPOTIPY_REDIRECT_URI`. |
| `ECHOFY_OAUTH_SUCCESS_URL` | Browser redirect after successful Spotify login. |
| **Database** | |
| `AZURE_SQL_CONNECTION_STRING` | Full ODBC connection string for Azure SQL (uses SQLite if not set). |
| `DATABASE_URL` | Any SQLAlchemy URI — used if `AZURE_SQL_CONNECTION_STRING` is not set. |
| **Azure Blob (profile photos)** | |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage account connection string; enables `POST/DELETE /api/auth/profile/photo`. |
| `AZURE_STORAGE_CONTAINER_PROFILES` | Blob container name (default `echofy-profiles`). |
| **CORS / Static Web Apps** | |
| `ECHOFY_SWA_URL`, `ECHOFY_CORS_ORIGINS`, … | Comma-separated allowed browser origins for the API (see [`.env.example`](.env.example)). |
| **Discord (optional)** | |
| `DISCORD_WEBHOOK_URL` | Discord incoming webhook; server posts client error summaries from `/api/telemetry/client-error`. Alias: `ECHOFY_DISCORD_WEBHOOK_URL`. |

### Static Web Apps (frontend) and API base URL

The browser loads **`/echofy-config.json`** on the deployed site to read `{ "apiBase": "https://your-backend..." }`. GitHub Actions writes that file before deploy from **`ECHOFY_BACKEND_URL`** (HTTPS API origin, no trailing slash). Configure it under **Settings → Secrets and variables → Actions**:

- **Variables** (recommended for a normal public App Service URL): create repository variable **`ECHOFY_BACKEND_URL`**.
- **Secrets** (optional): same name **`ECHOFY_BACKEND_URL`** if you prefer the value masked in logs; if both variable and secret exist, the **secret** is used.

For local testing against a remote API, copy [`frontend/public/echofy-config.example.json`](frontend/public/echofy-config.example.json) to `frontend/public/echofy-config.json` (that file is gitignored).

### Database admin CLI

From the repo root (venv activated): **`python scripts/admin_cli.py`**. Loads `app` from `backend/` using the same `.env` database settings as the server.

### Discord bug alerts (optional)

Set **`DISCORD_WEBHOOK_URL`** in repo-root `.env` (and in **Azure App Service** application settings for production) to an [incoming webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL. When a browser action fails (network or unexpected errors), the frontend calls **`POST /api/telemetry/client-error`** and the API posts a **sanitized** JSON summary to Discord. Passwords and similar fields are stripped server-side. If the variable is unset, reports are accepted but not forwarded. Treat the webhook URL like a secret; if it leaks, regenerate it in Discord.
