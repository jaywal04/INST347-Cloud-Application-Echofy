"""Add missing columns on `users` to match the SQLAlchemy User model (Azure SQL / SQLite).

`db.create_all()` does not alter existing tables; this runs after create_all on startup.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, String, inspect, text
from sqlalchemy.schema import Column

from app.models import User


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
    if name == "accepted_terms":
        return "0"
    if name in ("profile_public", "show_listening_history", "show_reviews"):
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
    if name == "accepted_terms":
        return "0"
    if name in ("profile_public", "show_listening_history", "show_reviews"):
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


def ensure_user_table_columns(engine) -> None:
    table = User.__table__
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
