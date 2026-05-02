"""Database configuration — SQLite locally, Azure SQL when credentials are provided."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def apply_remote_db_engine_options(app: Flask) -> None:
    """Azure SQL/MySQL and similar hosts often close idle TCP connections; refresh pooled conns."""
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri or uri.startswith("sqlite"):
        return
    opts = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    opts.setdefault("pool_pre_ping", True)
    opts.setdefault("pool_recycle", 300)
    opts.setdefault("pool_timeout", 30)
    opts.setdefault("pool_size", 5)
    opts.setdefault("max_overflow", 2)
    # MySQL uses connect_timeout; MSSQL/others use timeout
    if uri.startswith("mysql"):
        opts.setdefault("connect_args", {"connect_timeout": 30})
    else:
        opts.setdefault("connect_args", {"timeout": 30})
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = opts


def _inject_mysql_charset(uri: str) -> str:
    """Ensure charset=utf8mb4 is present in a MySQL connection URI.

    Without utf8mb4, MySQL silently truncates 4-byte emoji to '?'.
    """
    if not uri.lower().startswith("mysql"):
        return uri
    sep = "&" if "?" in uri else "?"
    if "charset=" not in uri.lower():
        uri = f"{uri}{sep}charset=utf8mb4"
    return uri


def _build_database_uri() -> str:
    """Return the SQLAlchemy database URI based on available env vars.

    Priority:
      1. AZURE_SQL_CONNECTION_STRING  – full ODBC string for Azure SQL
      2. DATABASE_URL                 – any SQLAlchemy URI (Postgres, MySQL, etc.)
      3. Fall back to local SQLite file  (instance/echofy.db)
    """
    azure_conn = os.environ.get("AZURE_SQL_CONNECTION_STRING", "").strip()
    if azure_conn:
        # pyodbc connection string for Azure SQL
        # Example: "Driver={ODBC Driver 18 for SQL Server};Server=tcp:myserver.database.windows.net,1433;Database=echofy;Uid=admin;Pwd=secret;Encrypt=yes;TrustServerCertificate=no;"
        # Inject ODBC driver-level retry so the driver waits for a paused DB to wake up
        for param, val in [("ConnectRetryCount", "3"), ("ConnectRetryInterval", "10")]:
            if param.lower() not in azure_conn.lower():
                azure_conn = azure_conn.rstrip(";") + f";{param}={val};"
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(azure_conn)}"

    generic = os.environ.get("DATABASE_URL", "").strip()
    if generic:
        return _inject_mysql_charset(generic)

    db_path = Path(__file__).resolve().parent.parent / "instance" / "echofy.db"
    db_path.parent.mkdir(exist_ok=True)
    return f"sqlite:///{db_path}"


def init_db(app):
    """Bind SQLAlchemy to *app*, create tables if missing, then align `users` columns."""
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", _build_database_uri())
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    apply_remote_db_engine_options(app)
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            from app.schema_sync import ensure_model_table_columns
            ensure_model_table_columns(db.engine)
        except Exception as exc:
            # Database temporarily unavailable (e.g. Azure SQL auto-pause, cold start).
            # Log and continue — the app will serve requests and DB errors are handled
            # per-route via the OperationalError/DBAPIError error handlers.
            import logging
            logging.getLogger(__name__).warning(
                "DB schema sync skipped on startup (will retry on first request): %s", exc
            )
