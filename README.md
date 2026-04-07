## Project layout

| Path | Purpose |
|------|---------|
| `frontend/public/` | Static site served locally and deployed to Azure Static Web Apps |
| `frontend/src/` | Front-end source (framework code, bundles) as you grow beyond plain HTML/CSS/JS |
| `backend/app/` | Backend application package (API, services, auth, database) |
| `backend/tests/` | Backend tests |
| `api/` | Optional Azure Static Web Apps Functions (set `api_location` in the workflow when used) |

The prototype script `echofy_model_prototype.py` lives in `backend/` at the repo root of that folder.

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
| Both at once | **3000** + **5000** | `start.bat` (Windows) or `./start.sh` (macOS / Linux) opens two terminal windows |
| Frontend only | **3000** | `start.bat frontend` or `./start.sh frontend` (optional: `PORT=8080 ./start.sh frontend`) |
| Backend only | **5000** | `start.bat backend` or `./start.sh backend` (optional: `PORT=5001 ./start.sh backend`) |

Check the API with [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health).

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
| `GET` | `/api/auth/me` | Check current session (returns `{ authenticated, user }`) |

### Database

By default, the backend uses **SQLite** (`backend/instance/echofy.db`) — no setup required, the database file is created automatically on first run.

To use **Azure SQL** in production, set `AZURE_SQL_CONNECTION_STRING` in your `.env`:

```
AZURE_SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=tcp:yourserver.database.windows.net,1433;Database=echofy;Uid=admin;Pwd=yourpassword;Encrypt=yes;TrustServerCertificate=no;
```

The app switches automatically — no code changes needed. You can also set `DATABASE_URL` for any other SQLAlchemy-compatible database (PostgreSQL, MySQL, etc.).

<hr>

## Spotify (Discover page)

1. In the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), add a **Redirect URI** that matches **`SPOTIFY_REDIRECT_URI`** in your `.env` (default `http://127.0.0.1:5000/callback`). Spotify often rejects `localhost`; **`127.0.0.1`** is fine.
2. Set **`SPOTIFY_CLIENT_ID`** and **`SPOTIFY_CLIENT_SECRET`** in repo-root `.env` (see [`.env.example`](.env.example)). Older **`JAY_SPOTIFY_*`** names are still read if the `SPOTIFY_*` variables are empty.
3. **Connect Spotify** on the Discover page (or open `http://127.0.0.1:5000/auth/spotify`) to sign in; after callback, **your top tracks** are used when you click “Show top Spotify music,” with chart fallbacks when needed.
4. Without a connected session, **Client Credentials** loads chart-style data (Top 50 if allowed, else new releases / featured playlists) when ID and secret are set.
5. For local OAuth, open the frontend at **`http://127.0.0.1:3000`** (not `localhost`) so the session cookie is sent to **`http://127.0.0.1:5000`** on API calls.
6. Optional **`SPOTIFY_TOKEN`**: same behavior as a connected user token without the browser flow (legacy **`JAY_SPOTIFY_TOKEN`** if `SPOTIFY_TOKEN` is empty).

<hr>

## Environment variables

All variables go in a `.env` file at the repo root. The static frontend does **not** read `.env`; it only calls the API.

| Variable | Purpose |
|----------|---------|
| `PORT` | Flask port (default `5000`). |
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
