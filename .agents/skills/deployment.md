# Echofy — deployment

**When to read this:** CI/CD, Azure, or wiring the static site to the API URL.

## Split hosting

| Component | Typical target |
|-----------|----------------|
| Flask API | Azure App Service (Python 3.12) |
| Static frontend | Azure Static Web Apps (`frontend/public` as app root) |

## Backend — GitHub Actions

Workflow: `.github/workflows/main_echofy-backend.yml`

- Triggers: push to `main`, `workflow_dispatch`.
- Installs `requirements.txt`, smoke-imports `from app.main import app` with `PYTHONPATH=backend`.
- Stages `backend/app` → `deploy/app`, plus root `requirements.txt` and `backend/startup.sh`, then deploys with `azure/webapps-deploy@v3` using a publish profile secret.

App Service sets `PORT`, `WEBSITE_HOSTNAME`, etc.; align session/CORS env vars for HTTPS + SWA origin (see `security.md` and `.env.example`).

## Frontend — Static Web Apps

Workflow: `.github/workflows/azure-static-web-apps-polite-mud-0e527350f.yml`

1. **Write `frontend/public/echofy-config.json`** — Python inline step reads `secrets.ECHOFY_BACKEND_URL` or `vars.ECHOFY_BACKEND_URL` (secret wins), strips trailing slash, writes `{"apiBase":"<url>"}`. If unset, may fall back to parsing `echofy-config.example.json` for CI only — production should set the variable/secret explicitly.
2. **Render HTML** — `python scripts/render_static_html.py`
3. **Deploy** — `Azure/static-web-apps-deploy@v1` with `app_location: frontend/public`, `skip_app_build: true`

Repository needs `AZURE_STATIC_WEB_APPS_API_TOKEN_*` secret for the SWA resource.

## Local static against remote API

Copy `frontend/public/echofy-config.example.json` to `echofy-config.json` (gitignored) with the real API base URL.

## Optional container

Repo may include a `Dockerfile` for Container Apps; App Service path above is the primary documented flow in `README.md`.

## Checklist for new environments

- [ ] API: `FLASK_SECRET_KEY`, DB connection, Spotify credentials, `ECHOFY_PRODUCTION` or Azure host for session cookies.
- [ ] CORS: `ECHOFY_SWA_URL` or `ECHOFY_CORS_ORIGINS` matching the static site origin(s).
- [ ] SWA: `ECHOFY_BACKEND_URL` in GitHub Actions for `echofy-config.json`.
- [ ] Spotify Dashboard: redirect URI matches deployed callback URL (HTTPS in production).
