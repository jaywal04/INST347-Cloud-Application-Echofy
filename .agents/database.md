# Echofy — database

**When to read this:** Migrations mentally, connection errors, new columns, or local SQLite vs cloud.

## URI selection (`backend/app/database.py`)

Priority:

1. **`AZURE_SQL_CONNECTION_STRING`** — Full ODBC string; SQLAlchemy URI becomes `mssql+pyodbc:///?odbc_connect=...` (URL-encoded). Driver-level retry params may be injected for paused DB wake-up.
2. **`DATABASE_URL`** — Any SQLAlchemy URI (e.g. PostgreSQL).
3. **SQLite fallback** — File at `backend/instance/echofy.db` (directory created if missing).

## Engine options (remote only)

`apply_remote_db_engine_options` skips SQLite, then sets pool defaults: `pool_pre_ping`, `pool_recycle`, `pool_timeout`, `pool_size`, `max_overflow`, `connect_args` — aimed at Azure SQL idle disconnects.

## Startup / schema

- `init_db(app)` registers SQLAlchemy, `db.create_all()`, then `schema_sync.ensure_model_table_columns` to add missing columns on existing tables (especially `users`) across SQLite and Azure SQL.
- If DB is unreachable at startup, warning is logged; routes handle `OperationalError` / `DBAPIError` with 503.

## Models (`backend/app/models.py`)

| Table | Purpose |
|-------|---------|
| `users` | `User` — credentials, profile, privacy flags, `spotify_access_token`, `spotify_refresh_token`, optional `profile_image_url` |
| `pending_verifications` | Email codes for signup / delete flows |
| `friend_requests` | Directed requests (`from_user_id`, `to_user_id`, `status`); unique on (from, to); FK `NO ACTION` to satisfy SQL Server cascade rules |
| `song_reviews` | Per-user ratings/reviews keyed by `item_hash` (SHA-256 of canonical item key); unique (user_id, item_hash) |

## Time storage

`utcnow_naive()` stores UTC as naive `DateTime` for broad DB compatibility.

## Friend graph

Accepted friendship is represented by a `friend_requests` row with `status='accepted'` (not a separate edges table).
