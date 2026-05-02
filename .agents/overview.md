# Echofy — project overview

**When to read this:** First pass on the repo; orientation before touching frontend, API, or deploy.

## What it is

Echofy is a static web app plus a Python API: music discovery (Spotify), song reviews, user profiles, friends, and notifications. Users sign up with email verification, log in via Flask sessions, and optionally connect Spotify for personalized charts and search.

## Tech stack

| Layer | Technology |
|-------|------------|
| API | Flask, Flask-Login, Flask-CORS, SQLAlchemy |
| DB | SQLite (default), Azure SQL (ODBC), or any SQLAlchemy URI |
| Frontend | Static HTML + vanilla JS under `frontend/public/` |
| Hosting | Azure App Service (API), Azure Static Web Apps (frontend) |

## Repository map

| Path | Role |
|------|------|
| `backend/app/` | Flask app (`main.py`), blueprints (`auth`, `friends`, `reviews`, `telemetry`), models, Spotify client, blob/email helpers |
| `frontend/snippets/` | Source fragments: `layout-top.html`, `bodies/*.html`, `footers/*.html` |
| `frontend/public/` | **Built** static site (HTML, `js/`, `css/`) — regenerate from snippets |
| `scripts/render_static_html.py` | Assembles `public/*.html` from snippets |
| `.github/workflows/` | Backend deploy (Web App), SWA deploy (writes `echofy-config.json`, runs render script) |
| `.env` (repo root) | Backend secrets and config (see `.env.example`) |

## Ports and local run

| Service | Default port | Notes |
|---------|--------------|-------|
| Frontend static server | **3001** | `frontend/server.py` or `start.sh frontend` |
| Flask API | **5001** | `PORT` env; `start.sh backend` |

Use `start.bat` / `start.sh` from the repo root to launch both. Health check: `GET http://127.0.0.1:5001/api/health`.

## Critical workflow for HTML

After editing anything under `frontend/snippets/`, run from repo root:

```bash
python scripts/render_static_html.py
```

Commit the updated `frontend/public/*.html`. CI runs the same step before Static Web Apps deploy.

## Deep-dive docs (same folder)

- `frontend.md` — snippets, JS modules, API base, SWA routing
- `backend.md` — app factory, sessions, CORS, blueprints
- `api.md` — route catalog
- `database.md` — URI selection, models, schema sync
- `spotify_api.md` — OAuth, tokens, Web API usage
- `security.md` — cookies, CORS, OAuth return validation, secrets
- `deployment.md` — GitHub Actions, Azure
- `integrations.md` — Blob, email, Discord

Authoritative env reference: [`.env.example`](../../.env.example). Human-oriented setup: [`README.md`](../../README.md).
