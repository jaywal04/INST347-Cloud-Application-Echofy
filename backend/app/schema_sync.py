"""Add missing columns on existing tables to match the SQLAlchemy models.

`db.create_all()` creates missing tables, but it does not alter existing ones.
This startup sync fills in missing columns for legacy SQLite/Azure SQL tables.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, String, inspect, text
from sqlalchemy.schema import Column

from app.models import (
    FriendRequest,
    PendingVerification,
    ReviewLike,
    ReviewReaction,
    SongReview,
    User,
)


def _quote_table_sqlite(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_table_mssql(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def _mssql_type_sql(col: Column) -> str:
    t = col.type
    if isinstance(t, Integer):
        return "INT"
    if isinstance(t, String):
        return f"NVARCHAR({t.length or 255})"
    if isinstance(t, Boolean):
        return "BIT"
    if isinstance(t, DateTime):
        return "DATETIME2"
    return "NVARCHAR(255)"


def _mssql_default_sql(col: Column) -> str | None:
    if col.nullable:
        return None
    name = col.name.lower()
    if name in ("accepted_terms", "attempts"):
        return "0"
    if name in ("profile_public", "show_listening_history", "show_reviews", "show_bio", "show_genre"):
        return "1"
    if name == "created_at":
        return "SYSUTCDATETIME()"
    if getattr(col, "default", None) is not None and getattr(col.default, "arg", None) is not None:
        arg = col.default.arg
        if callable(arg):
            return None
        if isinstance(arg, bool):
            return "1" if arg else "0"
        if isinstance(arg, int):
            return str(arg)
        if isinstance(arg, str):
            return "N'" + arg.replace("'", "''") + "'"
    return None


def _mssql_column_ddl(col: Column) -> str:
    q = _quote_table_mssql(col.name)
    typ = _mssql_type_sql(col)
    if col.nullable:
        return f"{q} {typ} NULL"
    default_sql = _mssql_default_sql(col)
    if default_sql:
        return f"{q} {typ} NOT NULL DEFAULT {default_sql}"
    return f"{q} {typ} NOT NULL"


def _sqlite_type_sql(col: Column) -> str:
    t = col.type
    if isinstance(t, Integer):
        return "INTEGER"
    if isinstance(t, Boolean):
        return "INTEGER"
    if isinstance(t, DateTime):
        return "DATETIME"
    if isinstance(t, String):
        return "TEXT"
    return "TEXT"


def _sqlite_default_sql(col: Column) -> str | None:
    if col.nullable:
        return None
    name = col.name.lower()
    if name in ("accepted_terms", "attempts"):
        return "0"
    if name in ("profile_public", "show_listening_history", "show_reviews", "show_bio", "show_genre"):
        return "1"
    if name == "created_at":
        return "CURRENT_TIMESTAMP"
    return None


def _sqlite_column_ddl(col: Column) -> str:
    q = _quote_table_sqlite(col.name)
    typ = _sqlite_type_sql(col)
    if col.nullable:
        return f"{q} {typ}"
    default_sql = _sqlite_default_sql(col)
    if default_sql:
        return f"{q} {typ} NOT NULL DEFAULT {default_sql}"
    return f"{q} {typ} NOT NULL"


def _ensure_table_columns(engine, table) -> None:
    table_name = table.name
    dialect_name = engine.dialect.name

    if dialect_name not in ("sqlite", "mssql"):
        return

    insp = inspect(engine)
    if not insp.has_table(table_name):
        return

    existing = {c["name"].lower() for c in insp.get_columns(table_name)}

    if dialect_name == "mssql":
        qtable = _quote_table_mssql(table_name)
        ddl_fn = _mssql_column_ddl
    else:
        qtable = _quote_table_sqlite(table_name)
        ddl_fn = _sqlite_column_ddl

    for col in table.columns:
        if col.primary_key:
            continue
        if col.name.lower() in existing:
            continue
        fragment = ddl_fn(col)
        stmt = text(f"ALTER TABLE {qtable} ADD {fragment}")
        with engine.begin() as conn:
            conn.execute(stmt)
        existing.add(col.name.lower())


def _review_likes_has_user_pair_unique(insp, table_name: str) -> bool:
    """True if DB already enforces at most one like per (user_id, song_review_id)."""
    for uc in insp.get_unique_constraints(table_name):
        cols = {c.lower() for c in (uc.get("column_names") or [])}
        if cols == {"user_id", "song_review_id"}:
            return True
    for ix in insp.get_indexes(table_name):
        if not ix.get("unique"):
            continue
        cols = {c.lower() for c in (ix.get("column_names") or [])}
        if cols == {"user_id", "song_review_id"}:
            return True
    return False


def ensure_review_likes_one_per_user(engine) -> None:
    """Legacy DBs may lack the model's unique constraint; dedupe rows then add it."""
    dialect_name = engine.dialect.name
    if dialect_name not in ("sqlite", "mssql"):
        return

    table_name = ReviewLike.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return
    if _review_likes_has_user_pair_unique(insp, table_name):
        return

    if dialect_name == "sqlite":
        q = _quote_table_sqlite(table_name)
        dedupe = text(
            f"DELETE FROM {q} WHERE id NOT IN ("
            f"SELECT MIN(id) FROM {q} GROUP BY user_id, song_review_id)"
        )
        idx = text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS uq_review_likes_user_review "
            f"ON {q} (user_id, song_review_id)"
        )
        with engine.begin() as conn:
            conn.execute(dedupe)
            conn.execute(idx)
        return

    q = _quote_table_mssql(table_name)
    dedupe = text(
        f"WITH d AS (SELECT id, ROW_NUMBER() OVER ("
        f"PARTITION BY user_id, song_review_id ORDER BY id) AS rn FROM {q}) "
        f"DELETE FROM {q} WHERE id IN (SELECT id FROM d WHERE rn > 1)"
    )
    idx = text(
        f"CREATE UNIQUE NONCLUSTERED INDEX uq_review_likes_user_review "
        f"ON {q} (user_id, song_review_id)"
    )
    with engine.begin() as conn:
        conn.execute(dedupe)
        conn.execute(idx)


def _review_reactions_has_triple_unique(insp, table_name: str) -> bool:
    for uc in insp.get_unique_constraints(table_name):
        cols = {c.lower() for c in (uc.get("column_names") or [])}
        if cols == {"user_id", "song_review_id", "emoji"}:
            return True
    for ix in insp.get_indexes(table_name):
        if not ix.get("unique"):
            continue
        cols = {c.lower() for c in (ix.get("column_names") or [])}
        if cols == {"user_id", "song_review_id", "emoji"}:
            return True
    return False


def ensure_review_reactions_one_per_user_emoji(engine) -> None:
    dialect_name = engine.dialect.name
    if dialect_name not in ("sqlite", "mssql"):
        return
    table_name = ReviewReaction.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return
    if _review_reactions_has_triple_unique(insp, table_name):
        return

    if dialect_name == "sqlite":
        q = _quote_table_sqlite(table_name)
        dedupe = text(
            f"DELETE FROM {q} WHERE id NOT IN ("
            f"SELECT MIN(id) FROM {q} GROUP BY user_id, song_review_id, emoji)"
        )
        idx = text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS uq_review_reactions_user_review_emoji "
            f"ON {q} (user_id, song_review_id, emoji)"
        )
        with engine.begin() as conn:
            conn.execute(dedupe)
            conn.execute(idx)
        return

    q = _quote_table_mssql(table_name)
    dedupe = text(
        f"WITH d AS (SELECT id, ROW_NUMBER() OVER ("
        f"PARTITION BY user_id, song_review_id, emoji ORDER BY id) AS rn FROM {q}) "
        f"DELETE FROM {q} WHERE id IN (SELECT id FROM d WHERE rn > 1)"
    )
    idx = text(
        f"CREATE UNIQUE NONCLUSTERED INDEX uq_review_reactions_user_review_emoji "
        f"ON {q} (user_id, song_review_id, emoji)"
    )
    with engine.begin() as conn:
        conn.execute(dedupe)
        conn.execute(idx)


def ensure_model_table_columns(engine) -> None:
    for table in (
        User.__table__,
        PendingVerification.__table__,
        FriendRequest.__table__,
        SongReview.__table__,
        ReviewLike.__table__,
        ReviewReaction.__table__,
    ):
        _ensure_table_columns(engine, table)
    ensure_review_likes_one_per_user(engine)
    ensure_review_reactions_one_per_user_emoji(engine)
