"""Database configuration — SQLite locally, Azure SQL when credentials are provided."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def apply_remote_db_engine_options(app: Flask) -> None:
    """Azure SQL and similar hosts often close idle TCP connections; refresh pooled conns."""
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if not uri or uri.startswith("sqlite"):
        return
    opts = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    opts.setdefault("pool_pre_ping", True)
    opts.setdefault("pool_recycle", 300)
    opts.setdefault("pool_timeout", 60)
    opts.setdefault("pool_size", 5)
    opts.setdefault("max_overflow", 2)
    opts.setdefault("connect_args", {"timeout": 60})
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = opts


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
        for param, val in [("ConnectRetryCount", "6"), ("ConnectRetryInterval", "10"), ("Connection Timeout", "60")]:
            if param.lower() not in azure_conn.lower():
                azure_conn = azure_conn.rstrip(";") + f";{param}={val};"
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(azure_conn)}"

    generic = os.environ.get("DATABASE_URL", "").strip()
    if generic:
        return generic

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
        db.create_all()
        from app.schema_sync import ensure_model_table_columns

        ensure_model_table_columns(db.engine)
