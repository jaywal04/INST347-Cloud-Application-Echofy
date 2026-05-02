"""
Echofy Admin CLI
~~~~~~~~~~~~~~~~
Interactive admin tool for managing the database.

Usage (from repo root, with venv activated and ``pip install -r requirements.txt``):

    python backend/app/admin/admin_cli.py

Or from the ``backend`` directory: ``python -m app.admin.admin_cli``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ``__file__`` is backend/app/admin/admin_cli.py → parents[2] is the backend folder (app package root).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND_ROOT))

from flask import Flask
from sqlalchemy import func, inspect, or_, text

from app.database import apply_remote_db_engine_options, db, _build_database_uri
from app.models import FriendRequest, User


def create_admin_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _build_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    apply_remote_db_engine_options(app)
    db.init_app(app)
    return app


app = create_admin_app()


def _resolve_user(identifier: str) -> User | None:
    """Look up a user by numeric ID, email (case-insensitive), or username."""
    s = (identifier or "").strip()
    if not s:
        return None
    if s.isdigit():
        return User.query.get(int(s))
    if "@" in s:
        return User.query.filter(func.lower(User.email) == s.lower()).first()
    return User.query.filter_by(username=s).first()


MENU = """
============================================
           ECHOFY ADMIN CONSOLE
============================================
  1) List all tables
  2) Show table data
  3) List all users
  4) View user details
  5) Delete a user
  6) Count rows in a table
  7) Run custom SQL query (SELECT only)
  8) Reset a user's password
  0) Exit
============================================
"""


def list_tables():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if not tables:
        print("\n  No tables found in the database.")
        return
    print(f"\n  Tables ({len(tables)}):")
    for t in tables:
        cols = inspector.get_columns(t)
        print(f"    - {t}  ({len(cols)} columns)")


def show_table_data():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if not tables:
        print("\n  No tables found.")
        return

    print("\n  Available tables:", ", ".join(tables))
    name = input("  Table name: ").strip()
    if name not in tables:
        print(f"  Table '{name}' not found.")
        return

    limit = input("  Max rows to show (default 50): ").strip()
    limit = int(limit) if limit.isdigit() else 50

    result = db.session.execute(text(f"SELECT * FROM [{name}]").columns(), {})  # noqa: S608
    # Use raw text query to stay db-agnostic
    result = db.session.execute(text(f"SELECT * FROM [{name}]"))
    rows = result.fetchmany(limit)
    columns = result.keys()

    if not rows:
        print(f"\n  Table '{name}' is empty.")
        return

    # Print header
    col_list = list(columns)
    print(f"\n  {name} ({len(rows)} row{'s' if len(rows) != 1 else ''} shown):")
    print("  " + " | ".join(f"{c:>20}" for c in col_list))
    print("  " + "-" * (23 * len(col_list)))

    for row in rows:
        vals = []
        for v in row:
            s = str(v) if v is not None else "NULL"
            if len(s) > 20:
                s = s[:17] + "..."
            vals.append(f"{s:>20}")
        print("  " + " | ".join(vals))


def list_users():
    users = User.query.order_by(User.id).all()
    if not users:
        print("\n  No users found.")
        return

    print(f"\n  Users ({len(users)}):")
    print(f"  {'ID':>5}  {'Username':<20}  {'Email':<30}  {'Created'}")
    print(f"  {'-'*5}  {'-'*20}  {'-'*30}  {'-'*20}")
    for u in users:
        created = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "N/A"
        print(f"  {u.id:>5}  {u.username:<20}  {u.email:<30}  {created}")


def view_user():
    identifier = input("\n  Enter user ID, username, or email: ").strip()
    if not identifier:
        return

    user = _resolve_user(identifier)

    if not user:
        print(f"  User '{identifier}' not found.")
        return

    print(f"\n  User Details:")
    print(f"    ID:                {user.id}")
    print(f"    Username:          {user.username}")
    print(f"    Email:             {user.email}")
    print(f"    Age:               {user.age or 'N/A'}")
    print(f"    Sex:               {user.sex or 'N/A'}")
    print(f"    Bio:               {user.bio or 'N/A'}")
    print(f"    Location:          {user.location or 'N/A'}")
    print(f"    Favorite Genre:    {user.favorite_genre or 'N/A'}")
    print(f"    Profile Public:    {user.profile_public}")
    print(f"    Show History:      {user.show_listening_history}")
    print(f"    Show Reviews:      {user.show_reviews}")
    print(f"    Accepted Terms:    {user.accepted_terms}")
    created = user.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if user.created_at else "N/A"
    print(f"    Created At:        {created}")


def delete_user():
    identifier = input("\n  Enter user ID, username, or email to delete: ").strip()
    if not identifier:
        return

    user = _resolve_user(identifier)

    if not user:
        print(f"  User '{identifier}' not found.")
        return

    print(f"\n  About to delete: {user.username} ({user.email}), ID={user.id}")
    confirm = input("  Type 'DELETE' to confirm: ").strip()
    if confirm != "DELETE":
        print("  Cancelled.")
        return

    FriendRequest.query.filter(
        or_(FriendRequest.from_user_id == user.id, FriendRequest.to_user_id == user.id)
    ).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
    print(f"  User '{user.username}' has been deleted.")


def count_rows():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if not tables:
        print("\n  No tables found.")
        return

    print(f"\n  Row counts:")
    for t in tables:
        result = db.session.execute(text(f"SELECT COUNT(*) FROM [{t}]"))
        count = result.scalar()
        print(f"    {t:<30} {count} rows")


def run_query():
    print("\n  Enter a SELECT query (read-only):")
    query = input("  > ").strip()
    if not query:
        return

    # Safety check — only allow SELECT
    if not query.upper().lstrip().startswith("SELECT"):
        print("  Only SELECT queries are allowed.")
        return

    try:
        result = db.session.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()

        if not rows:
            print("  Query returned no results.")
            return

        col_list = list(columns)
        print(f"\n  Results ({len(rows)} rows):")
        print("  " + " | ".join(f"{c:>20}" for c in col_list))
        print("  " + "-" * (23 * len(col_list)))

        for row in rows:
            vals = []
            for v in row:
                s = str(v) if v is not None else "NULL"
                if len(s) > 20:
                    s = s[:17] + "..."
                vals.append(f"{s:>20}")
            print("  " + " | ".join(vals))
    except Exception as e:
        print(f"  Error: {e}")


def reset_password():
    identifier = input("\n  Enter user ID, username, or email: ").strip()
    if not identifier:
        return

    user = _resolve_user(identifier)

    if not user:
        print(f"  User '{identifier}' not found.")
        return

    print(f"  Resetting password for: {user.username} ({user.email})")
    new_pw = input("  New password (min 8 chars): ").strip()
    if len(new_pw) < 8:
        print("  Password must be at least 8 characters. Cancelled.")
        return

    confirm = input("  Confirm new password: ").strip()
    if new_pw != confirm:
        print("  Passwords don't match. Cancelled.")
        return

    user.set_password(new_pw)
    db.session.commit()
    print(f"  Password updated for '{user.username}'.")


def main():
    with app.app_context():
        print("\n  Connected to:", app.config["SQLALCHEMY_DATABASE_URI"][:80] + "...")

        while True:
            print(MENU)
            choice = input("  Choose an option: ").strip()

            if choice == "1":
                list_tables()
            elif choice == "2":
                show_table_data()
            elif choice == "3":
                list_users()
            elif choice == "4":
                view_user()
            elif choice == "5":
                delete_user()
            elif choice == "6":
                count_rows()
            elif choice == "7":
                run_query()
            elif choice == "8":
                reset_password()
            elif choice == "0":
                print("\n  Goodbye.\n")
                sys.exit(0)
            else:
                print("  Invalid option.")


if __name__ == "__main__":
    main()
