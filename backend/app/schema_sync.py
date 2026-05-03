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


def _quote_table_mysql(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


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


def _mysql_type_sql(col: Column) -> str:
    t = col.type
    if isinstance(t, Integer):
        return "INT"
    if isinstance(t, String):
        # utf8mb4 required for emoji; explicit on every varchar column
        length = t.length or 255
        return f"VARCHAR({length}) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    if isinstance(t, Boolean):
        return "TINYINT(1)"
    if isinstance(t, DateTime):
        return "DATETIME"
    return "VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"


def _mysql_default_sql(col: Column) -> str | None:
    if col.nullable:
        return None
    name = col.name.lower()
    if name in ("accepted_terms", "attempts"):
        return "0"
    if name in ("profile_public", "show_listening_history", "show_reviews", "show_bio", "show_genre"):
        return "1"
    if name == "created_at":
        return "UTC_TIMESTAMP()"
    if getattr(col, "default", None) is not None and getattr(col.default, "arg", None) is not None:
        arg = col.default.arg
        if callable(arg):
            return None
        if isinstance(arg, bool):
            return "1" if arg else "0"
        if isinstance(arg, int):
            return str(arg)
        if isinstance(arg, str):
            return "'" + arg.replace("'", "''") + "'"
    return None


def _mysql_column_ddl(col: Column) -> str:
    q = _quote_table_mysql(col.name)
    typ = _mysql_type_sql(col)
    if col.nullable:
        return f"{q} {typ}"
    default_sql = _mysql_default_sql(col)
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

    if dialect_name not in ("sqlite", "mssql", "mysql"):
        return

    insp = inspect(engine)
    if not insp.has_table(table_name):
        return

    existing = {c["name"].lower() for c in insp.get_columns(table_name)}

    if dialect_name == "mssql":
        qtable = _quote_table_mssql(table_name)
        ddl_fn = _mssql_column_ddl
        add_keyword = "ADD"
    elif dialect_name == "mysql":
        qtable = _quote_table_mysql(table_name)
        ddl_fn = _mysql_column_ddl
        add_keyword = "ADD COLUMN"
    else:
        qtable = _quote_table_sqlite(table_name)
        ddl_fn = _sqlite_column_ddl
        add_keyword = "ADD"

    for col in table.columns:
        if col.primary_key:
            continue
        if col.name.lower() in existing:
            continue
        fragment = ddl_fn(col)
        stmt = text(f"ALTER TABLE {qtable} {add_keyword} {fragment}")
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
    if dialect_name not in ("sqlite", "mssql", "mysql"):
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

    if dialect_name == "mysql":
        q = _quote_table_mysql(table_name)
        # MySQL can't reference the same table in a subquery for DELETE directly
        dedupe = text(
            f"DELETE FROM {q} WHERE id NOT IN ("
            f"SELECT id FROM (SELECT MIN(id) AS id FROM {q} GROUP BY user_id, song_review_id) AS tmp)"
        )
        idx = text(
            f"CREATE UNIQUE INDEX uq_review_likes_user_review "
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
    if dialect_name not in ("sqlite", "mssql", "mysql"):
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

    if dialect_name == "mysql":
        q = _quote_table_mysql(table_name)
        dedupe = text(
            f"DELETE FROM {q} WHERE id NOT IN ("
            f"SELECT id FROM (SELECT MIN(id) AS id FROM {q} GROUP BY user_id, song_review_id, emoji) AS tmp)"
        )
        idx = text(
            f"CREATE UNIQUE INDEX uq_review_reactions_user_review_emoji "
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


def _clean_mysql_corrupted_reactions(engine) -> None:
    """Delete reaction rows whose emoji was corrupted to '?' by MySQL's 3-byte utf8 charset.

    Any emoji that was stored while the column used utf8 (not utf8mb4) became a sequence of
    ASCII '?' characters.  Real emoji are always non-ASCII, so deleting rows where emoji
    consists entirely of ASCII characters removes exactly the corrupted rows.
    """
    if engine.dialect.name != "mysql":
        return
    table_name = ReviewReaction.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return
    q = _quote_table_mysql(table_name)
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {q} WHERE `emoji` REGEXP '^[[:ascii:]]+$'"))


def _ensure_mysql_emoji_utf8mb4(engine) -> None:
    """ALTER the emoji column to utf8mb4 on MySQL if it isn't already.

    MySQL tables created without an explicit charset default to the server charset,
    which is often latin1 or utf8 (3-byte only) — both silently corrupt 4-byte emoji.
    This runs once at startup and is a no-op if the column is already utf8mb4.
    """
    if engine.dialect.name != "mysql":
        return
    table_name = ReviewReaction.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return
    with engine.begin() as conn:
        row = conn.execute(text(
            "SELECT CHARACTER_SET_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = :t AND COLUMN_NAME = 'emoji'"
        ), {"t": table_name}).fetchone()
    if row and row[0] and row[0].lower() == "utf8mb4":
        return
    q = _quote_table_mysql(table_name)
    with engine.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE {q} MODIFY COLUMN `emoji` "
            f"VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL"
        ))


def _ensure_mssql_emoji_nvarchar(engine) -> None:
    """ALTER the emoji column from VARCHAR to NVARCHAR on MSSQL if needed.

    db.create_all() maps String(32) → VARCHAR(32) on SQL Server, which is
    non-Unicode and silently corrupts 4-byte emoji to '?'.  NVARCHAR is required.
    The unique index on (user_id, song_review_id, emoji) must be dropped first,
    then recreated after the column type change.
    """
    if engine.dialect.name != "mssql":
        return
    table_name = ReviewReaction.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = :t AND COLUMN_NAME = 'emoji'"
        ), {"t": table_name}).fetchone()
    if row and row[0].upper() == "NVARCHAR":
        return
    q = _quote_table_mssql(table_name)
    # Drop the unique index/constraint that covers the emoji column before altering
    with engine.begin() as conn:
        conn.execute(text(
            f"IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = "
            f"'uq_review_reactions_user_review_emoji' AND object_id = OBJECT_ID(N'{table_name}')) "
            f"DROP INDEX [uq_review_reactions_user_review_emoji] ON {q}"
        ))
        conn.execute(text(
            f"ALTER TABLE {q} ALTER COLUMN [emoji] NVARCHAR(32) NOT NULL"
        ))
        conn.execute(text(
            f"CREATE UNIQUE NONCLUSTERED INDEX [uq_review_reactions_user_review_emoji] "
            f"ON {q} (user_id, song_review_id, emoji)"
        ))


def _clean_mssql_corrupted_reactions(engine) -> None:
    """Delete reaction rows whose emoji was corrupted to '?' by a VARCHAR column on MSSQL.

    Real emoji always contain at least one character outside printable ASCII (U+0020–U+007E).
    Rows where emoji has no such character are corrupted and safe to remove.
    """
    if engine.dialect.name != "mssql":
        return
    table_name = ReviewReaction.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return
    q = _quote_table_mssql(table_name)
    with engine.begin() as conn:
        conn.execute(text(
            f"DELETE FROM {q} WHERE PATINDEX('%[^ -~]%', [emoji]) = 0"
        ))


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
    _ensure_mssql_emoji_nvarchar(engine)
    _clean_mssql_corrupted_reactions(engine)
    _ensure_mysql_emoji_utf8mb4(engine)
    _clean_mysql_corrupted_reactions(engine)
