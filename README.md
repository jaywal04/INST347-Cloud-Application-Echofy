## Project layout

| Path | Purpose |
|------|---------|
| `frontend/public/` | Static site served locally and deployed to Azure Static Web Apps |
| `frontend/src/` | Front-end source (framework code, bundles) as you grow beyond plain HTML/CSS/JS |
| `backend/app/` | Backend application package (API, services) |
| `backend/tests/` | Backend tests |
| `api/` | Optional Azure Static Web Apps Functions (set `api_location` in the workflow when used) |

The prototype script `echofy_model_prototype.py` lives in `backend/` at the repo root of that folder.

## Local development (localhost)

| Service | Port | How to run |
|---------|------|------------|
| Both at once | **3000** + **5000** | `start.bat` (Windows) or `./start.sh` (macOS / Linux) opens two terminal windows |
| Frontend only | **3000** | `start.bat frontend` or `./start.sh frontend` (optional: `PORT=8080 ./start.sh frontend`) |
| Backend only | **5000** | `start.bat backend` or `./start.sh backend` (optional: `PORT=5001 ./start.sh backend`) |

Activate `.venv` and run `pip install -r requirements.txt` first. On Linux, `./start.sh` needs a supported terminal (GNOME Terminal, Konsole, XFCE Terminal, or xterm). Check the API with [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health).

### Spotify (Discover page)

1. In the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), add a **Redirect URI** that matches **`SPOTIFY_REDIRECT_URI`** in your `.env` (default `http://127.0.0.1:5000/callback`). Spotify often rejects `localhost`; **`127.0.0.1`** is fine.
2. Set **`SPOTIFY_CLIENT_ID`** and **`SPOTIFY_CLIENT_SECRET`** in repo-root `.env` (see [`.env.example`](.env.example)). Older **`JAY_SPOTIFY_*`** names are still read if the `SPOTIFY_*` variables are empty.
3. **Connect Spotify** on the Discover page (or open `http://127.0.0.1:5000/auth/spotify`) to sign in; after callback, **your top tracks** are used when you click “Show top Spotify music,” with chart fallbacks when needed.
4. Without a connected session, **Client Credentials** loads chart-style data (Top 50 if allowed, else new releases / featured playlists) when ID and secret are set.
5. For local OAuth, open the frontend at **`http://127.0.0.1:3000`** (not `localhost`) so the session cookie is sent to **`http://127.0.0.1:5000`** on API calls. Optional: **`ECHOFY_OAUTH_SUCCESS_URL`** (post-login redirect), **`FLASK_SECRET_KEY`** (session signing), **`SPOTIFY_MARKET`** (e.g. `US` for playlist `market=`).
6. Optional **`SPOTIFY_TOKEN`**: same behavior as a connected user token without the browser flow (legacy **`JAY_SPOTIFY_TOKEN`** if `SPOTIFY_TOKEN` is empty).

**Backend environment variables** (repo-root `.env`; loaded by [`backend/app/main.py`](backend/app/main.py)):

| Variable | Purpose |
|----------|---------|
| `PORT` | Flask port (default `5000`). On macOS/Linux, `PORT=8080 ./start.sh backend` is honored; set in System Environment on Windows if needed. |
| `SPOTIFY_CLIENT_ID` | Spotify Client ID (`JAY_SPOTIFY_CLIENT_ID` if empty). |
| `SPOTIFY_CLIENT_SECRET` | Spotify Client Secret (`JAY_SPOTIFY_CLIENT_SECRET` if empty). |
| `SPOTIFY_TOKEN` | Optional static user access token (`JAY_SPOTIFY_TOKEN` if empty). |
| `SPOTIFY_MARKET` | Optional ISO market for playlist requests (`JAY_SPOTIFY_MARKET` if empty; default `US`). |
| `SPOTIFY_REDIRECT_URI` | OAuth callback URL (must match Dashboard). Legacy: **`SPOTIPY_REDIRECT_URI`**. |
| `ECHOFY_OAUTH_SUCCESS_URL` | Browser redirect after successful Spotify login. |
| `FLASK_SECRET_KEY` | Signs session cookies (OAuth); change for production. |

The static frontend does **not** read `.env`; it only calls the API. No other Python modules read process environment except the Spotify client (market) and `main`.

<hr>

## Python virtual environment (`.venv`)

Create a virtual environment in the project root so dependencies stay isolated (says in the project not on your whole system). The `.venv` folder is gitignored.

### Windows (PowerShell or Command Prompt)

From the repo root:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `python` is not found, try `py -3` instead of `python`.

To leave the environment: `deactivate`

### macOS / Linux (Terminal)

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

To leave the environment: `deactivate`
