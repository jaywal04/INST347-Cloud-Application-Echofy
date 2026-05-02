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

## Spotify OAuth locally

Dashboard redirect URI should match **`http://127.0.0.1:5001/callback`** (Spotify often rejects `localhost` for the callback). Frontend can still be `http://localhost:3001` — see `spotify_api.md` / `security.md`.
