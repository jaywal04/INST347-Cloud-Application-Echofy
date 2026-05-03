# Echofy — database

**When to read this:** Migrations mentally, connection errors, new columns, or local SQLite vs cloud.

## URI selection (`backend/app/database.py`)

Priority:

1. **`AZURE_SQL_CONNECTION_STRING`** — Full ODBC string; SQLAlchemy URI becomes `mssql+pyodbc:///?odbc_connect=...` (URL-encoded). Driver-level retry params may be injected for paused DB wake-up.
2. **`DATABASE_URL`** — Any SQLAlchemy URI. **For MySQL**, `charset=utf8mb4` is automatically injected into the URL if not already present (required for emoji storage — plain `utf8` silently corrupts 4-byte characters to `?`).
3. **SQLite fallback** — File at `backend/instance/echofy.db` (directory created if missing).

`pymysql` is required in `requirements.txt` for MySQL connections (`mysql+pymysql://...`).

## Engine options (remote only)

`apply_remote_db_engine_options` skips SQLite, then sets pool defaults: `pool_pre_ping`, `pool_recycle`, `pool_timeout`, `pool_size`, `max_overflow`, `connect_args`. MySQL uses `connect_timeout`; MSSQL/others use `timeout`.

## Startup / schema

- `init_db(app)` registers SQLAlchemy, `db.create_all()`, then `schema_sync.ensure_model_table_columns` to add missing columns on existing tables across SQLite, MSSQL, and MySQL.
- If DB is unreachable at startup, warning is logged; routes handle `OperationalError` / `DBAPIError` with 503.

## Backward-compatible schema changes (deployed DBs)

**Rule:** schema changes made during development **must** still work after **commit, push, and deploy** when the server (or a developer) connects to an **older** database file or Azure SQL database that predates the change. Do not merge code that only works on a freshly deleted `echofy.db` unless the same PR also upgrades existing DBs on startup.

**What to do:**

- **New table:** add the SQLAlchemy model; `db.create_all()` creates it on next startup for DBs that did not have it. If you need extra indexes or constraints not created by `create_all()` on legacy stores, add logic in `backend/app/schema_sync.py` (see `ensure_review_likes_one_per_user` as a pattern).
- **New column on an existing table:** add the column on the model, then ensure `ensure_model_table_columns` runs for that table (include `Model.__table__` in `ensure_model_table_columns` if it is a new table name). Prefer nullable columns or sensible defaults so existing rows need no manual backfill.
- **New unique index / dedupe:** implement detection + optional dedupe + `CREATE UNIQUE INDEX` in `schema_sync` for SQLite, MSSQL, and MySQL as needed; never leave production with duplicate rows that would block the index.
- **Renames or destructive changes:** avoid unless unavoidable; if required, document a multi-step approach (add new column → backfill → switch reads → drop old) in this file.

**AGENTS.md / CLAUDE.md** require this policy at a high level; this section is the operational checklist.

## Models (`backend/app/models.py`)

| Table | Purpose |
|-------|---------|
| `users` | `User` — credentials, profile, privacy flags, `spotify_access_token`, `spotify_refresh_token`, optional `profile_image_url` |
| `pending_verifications` | Email codes for signup / delete flows |
| `friend_requests` | Directed requests (`from_user_id`, `to_user_id`, `status`); unique on (from, to); FK `NO ACTION` to satisfy SQL Server cascade rules |
| `song_reviews` | Per-user ratings/reviews keyed by `item_hash` (SHA-256 of canonical item key); unique (user_id, item_hash) |
| `review_likes` | `ReviewLike` — likes on reviews; **unique** `(user_id, song_review_id)`; `song_review_id` **ON DELETE CASCADE** (deleting a review removes its likes); `user_id` **ON DELETE NO ACTION** so SQL Server avoids error 1785 (multiple cascade paths from `users`). Account deletion removes the user’s like rows in app code before deleting `users`. |
| `review_reactions` | `ReviewReaction` — allowlisted emoji per review; **unique** `(user_id, song_review_id, emoji)`; same FK pattern as likes (`user_id` NO ACTION, `song_review_id` CASCADE); emoji values validated in `reviews.py` |
| `user_follows` | `UserFollow` — follower/followed edges; `follower_id` CASCADE, `followed_id` NO ACTION (see `auth.delete_account` cleanup) |
| `notifications` | `Notification` — `user_id` CASCADE, `actor_id` NO ACTION, `review_id` **NO ACTION** (not CASCADE): CASCADE on `review_id` would duplicate the CASCADE path from `users` via `song_reviews` and **SQL Server rejects the table (error 1785)**. Rows referencing a user’s reviews are deleted in app code before account deletion. |

## Time storage

`utcnow_naive()` stores UTC as naive `DateTime` for broad DB compatibility.

## Friend graph

Accepted friendship is represented by a `friend_requests` row with `status='accepted'` (not a separate edges table).
