# Echofy — external integrations

**When to read this:** Profile photos, verification email, Discord alerts, or optional Azure services.

## Azure Blob Storage (profile photos)

- **Module:** `backend/app/blob_storage.py`
- **Enabled when:** `AZURE_STORAGE_CONNECTION_STRING` is set; optional `AZURE_STORAGE_CONTAINER_PROFILES` (default container name `echofy-profiles`).
- **API:** `POST /api/auth/profile/photo`, `DELETE /api/auth/profile/photo` (`auth.py`); URLs may be signed for read access depending on container privacy.
- **Schema:** Startup `schema_sync` ensures `users` has needed columns when Blob is adopted.

## Email (signup / verification)

- **Module:** `backend/app/email_service.py` — uses **Resend** (`resend` Python SDK).
- **Env:** `RESEND_API_KEY` (required to send), optional `RESEND_EMAIL` for From address (defaults toward `noreply@echofy.com`).
- Sends verification codes for signup and account deletion flows (`PendingVerification` in `models.py`).

## Discord webhooks

- **Module:** `backend/app/discord_webhook.py`
- **Client errors:** `telemetry.py` → `send_client_bug_embed` when `DISCORD_WEBHOOK_URL` or `ECHOFY_DISCORD_WEBHOOK_URL` is set (`first_non_empty` in telemetry).
- **Startup ping:** `main.py` posts a green “API is running” embed unless `ECHOFY_DISCORD_NOTIFY_STARTUP` is `0`/`false`/`no`; skipped on Werkzeug reloader parent process in debug.

## Spotify

Covered in `spotify_api.md` — not duplicated here.

## Azure SQL

Covered in `database.md` — ODBC connection string env `AZURE_SQL_CONNECTION_STRING`.

## Telemetry endpoint

`POST /api/telemetry/client-error` accepts a JSON payload from the browser, sanitizes, rate-limits by IP, optionally forwards to Discord. Does not require authentication.
