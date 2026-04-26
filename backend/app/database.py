"""Database configuration — SQLite locally, Azure SQL when credentials are provided."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _parse_odbc_connection_string(conn: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for piece in conn.split(";"):
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        parts[key.strip().lower()] = value.strip()
    return parts


def _clean_sql_secret(value: str) -> str:
    text = (value or "").strip()
    if text.startswith("{") and text.endswith("}"):
        return text[1:-1]
    return text


def _parse_server_host_port(server_value: str) -> tuple[str, str]:
    server = (server_value or "").strip().replace("tcp:", "")
    if "," in server:
        host, port = server.rsplit(",", 1)
        host = host.strip()
        port = port.strip() or "1433"
        return host, port
    return server, "1433"


def _pyodbc_driver_available() -> bool:
    try:
        import pyodbc
    except Exception:
        return False
    return "ODBC Driver 18 for SQL Server" in set(pyodbc.drivers())


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
        if _pyodbc_driver_available():
            # pyodbc connection string for Azure SQL
            # Example: "Driver={ODBC Driver 18 for SQL Server};Server=tcp:myserver.database.windows.net,1433;Database=echofy;Uid=admin;Pwd=secret;Encrypt=yes;TrustServerCertificate=no;"
            # Inject ODBC driver-level retry so the driver waits for a paused DB to wake up
            for param, val in [("ConnectRetryCount", "6"), ("ConnectRetryInterval", "10"), ("Connection Timeout", "60")]:
                if param.lower() not in azure_conn.lower():
                    azure_conn = azure_conn.rstrip(";") + f";{param}={val};"
            return f"mssql+pyodbc:///?odbc_connect={quote_plus(azure_conn)}"

        parsed = _parse_odbc_connection_string(azure_conn)
        host, port = _parse_server_host_port(parsed.get("server", ""))
        database = parsed.get("database", "")
        username = quote_plus(parsed.get("uid", ""))
        password = quote_plus(_clean_sql_secret(parsed.get("pwd", "")))
        return (
            f"mssql+pymssql://{username}:{password}@{host}:{port}/{database}"
            "?charset=utf8&login_timeout=60&timeout=60"
        )

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
        try:
            db.create_all()
            from app.schema_sync import ensure_model_table_columns

            ensure_model_table_columns(db.engine)
        except Exception as exc:
            # Let the app boot even if Azure SQL is waking up; request-time handlers can retry later.
            app.logger.error("Database initialization skipped during startup: %s", exc)
