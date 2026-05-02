# Echofy — local development

**When to read this:** First time running the app, or when “it works on my machine” breaks.

## Prerequisites

- Python **3.12** (match CI / `README`).
- Repo root **virtualenv**: `python -m venv .venv` then activate and `pip install -r requirements.txt`.

## Ports

| Service | Port | Notes |
|---------|------|--------|
| Flask API | **5001** | `PORT` env overrides default in `backend/app/main.py` |
| Static frontend | **3001** | `frontend/server.py` / `start.sh frontend` |

## Run scripts (repo root)

- **Windows:** `start.bat` or `start.bat backend` / `start.bat frontend`
- **macOS/Linux:** `./start.sh` or `./start.sh backend` / `./start.sh frontend`

## Backend import path

Smoke import (as CI does):

```bash
PYTHONPATH=backend python -c "from app.main import app; assert app is not None"
```

Run the API with `PYTHONPATH=backend` so `from app...` resolves (see `README` / `start` scripts).

## Health check

Open or curl: `http://127.0.0.1:5001/api/health` → JSON `{"status":"ok"}`.

## Environment

Copy `.env.example` → `.env` at **repo root** (backend loads it from there). The static site does **not** read `.env`; it calls the API via `js/apiBase.js` / `echofy-config.json`.

### Database URI (SQLite vs Azure SQL)

`backend/app/database.py` picks the DB in this order: **`AZURE_SQL_CONNECTION_STRING`** → **`DATABASE_URL`** → SQLite under `backend/instance/echofy.db`.

- **`AZURE_STORAGE_CONNECTION_STRING`** is only for blob storage; it does **not** switch the SQL database.
- If you set Azure SQL in `.env` but the app still uses SQLite, check **Windows User or System environment variables** for an empty or old `AZURE_SQL_CONNECTION_STRING` / `DATABASE_URL`. The backend loads `.env` with **`override=True`**, so repo-root `.env` should win after a restart; if it still misbehaves, remove those keys from Windows env or sign out/in.
- Put the full ODBC string on **one line** in `.env`, or wrap it in **double quotes** if your editor wraps lines.

## Spotify OAuth locally

Dashboard redirect URI should match **`http://127.0.0.1:5001/callback`** (Spotify often rejects `localhost` for the callback). Frontend can still be `http://localhost:3001` — see `spotify_api.md` / `security.md`.
