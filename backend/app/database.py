"""Database configuration — SQLite locally, Azure SQL when credentials are provided."""

from __future__ import annotations

import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
        return f"mssql+pyodbc:///?odbc_connect={azure_conn}"

    generic = os.environ.get("DATABASE_URL", "").strip()
    if generic:
        return generic

    return "sqlite:///echofy.db"


def init_db(app):
    """Bind SQLAlchemy to *app* and create tables if they don't exist."""
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", _build_database_uri())
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)
    with app.app_context():
        db.create_all()
