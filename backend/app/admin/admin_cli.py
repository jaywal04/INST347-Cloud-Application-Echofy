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
from app.models import FriendRequest, ReviewReaction, User


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
  9) Reset review_reactions table (empty all rows)
  a) Diagnose emoji column (show type, constraints)
  b) Force fix emoji column to NVARCHAR (step-by-step)
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


def clear_review_reactions():
    count = db.session.query(func.count(ReviewReaction.id)).scalar()
    print(f"\n  review_reactions currently has {count} row(s).")
    if count == 0:
        print("  Table is already empty.")
        return
    confirm = input("  Type 'RESET' to empty the table (rows removed, table kept): ").strip()
    if confirm != "RESET":
        print("  Cancelled.")
        return
    db.session.query(ReviewReaction).delete(synchronize_session=False)
    db.session.commit()
    print(f"  Removed {count} reaction(s). Table is now empty.")


def diagnose_emoji_column():
    """Show the emoji column type, all indexes/constraints, and corrupted row count."""
    engine = db.engine
    if engine.dialect.name != "mssql":
        print("  This diagnostic is for MSSQL only.")
        return

    table_name = "review_reactions"
    print(f"\n  --- {table_name}.emoji DIAGNOSIS ---")

    # Column type
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLLATION_NAME "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = :t AND COLUMN_NAME = 'emoji'"
        ), {"t": table_name}).fetchone()
    if not row:
        print("  ERROR: Column 'emoji' not found.")
        return
    dtype, maxlen, nullable, collation = row
    print(f"\n  Column: emoji  Type: {dtype}({maxlen})  Nullable: {nullable}  Collation: {collation}")
    if dtype.upper() != "NVARCHAR":
        print("  -> NOT NVARCHAR — emoji stored as '??'. Needs ALTER COLUMN.")
    elif not collation or "BIN2" not in (collation or "").upper():
        print(f"  -> NVARCHAR but collation '{collation}' does NOT support supplementary characters.")
        print(f"  -> All emoji compare as EQUAL in the unique index — only one emoji per review allowed!")
        print(f"  -> Fix: ALTER to NVARCHAR(32) COLLATE Latin1_General_BIN2")
    else:
        print("  -> NVARCHAR with BIN2 collation. Emoji should work correctly.")

    # Key constraints
    print(f"\n  Key constraints on {table_name}:")
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT name, type_desc FROM sys.key_constraints "
            "WHERE parent_object_id = OBJECT_ID(:t)"
        ), {"t": table_name}).fetchall()
    if rows:
        for r in rows:
            print(f"    - {r[0]}  ({r[1]})")
    else:
        print("    (none)")

    # Indexes
    print(f"\n  Indexes on {table_name}:")
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT name, is_unique, is_unique_constraint, type_desc "
            "FROM sys.indexes "
            "WHERE object_id = OBJECT_ID(:t) AND name IS NOT NULL"
        ), {"t": table_name}).fetchall()
    if rows:
        for r in rows:
            print(f"    - {r[0]}  unique={r[1]}  is_constraint={r[2]}  type={r[3]}")
    else:
        print("    (none)")

    # Corrupted rows
    with engine.connect() as conn:
        count = conn.execute(text(
            "SELECT COUNT(*) FROM [review_reactions] "
            "WHERE PATINDEX('%[^ -~]%', [emoji]) = 0"
        )).scalar()
    print(f"\n  Corrupted rows (emoji stored as '?'): {count}")


def _force_clean_corrupted(engine, q):
    try:
        with engine.begin() as conn:
            result = conn.execute(text(
                f"DELETE FROM {q} WHERE PATINDEX('%[^ -~]%', [emoji]) = 0"
            ))
        print(f"    Deleted {result.rowcount} corrupted row(s).")
    except Exception as exc:
        print(f"    WARNING: Cleanup failed: {exc}")


def force_fix_emoji_column():
    """Step-by-step ALTER COLUMN emoji → NVARCHAR with full error output."""
    engine = db.engine
    if engine.dialect.name != "mssql":
        print("  This fix is for MSSQL only.")
        return

    table_name = "review_reactions"
    q = "[review_reactions]"
    idx_name = "uq_review_reactions_user_review_emoji"

    print(f"\n  --- Force fix {table_name}.emoji ---")

    # Check current type and collation
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT DATA_TYPE, COLLATION_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = :t AND COLUMN_NAME = 'emoji'"
        ), {"t": table_name}).fetchone()
    if not row:
        print("  ERROR: Cannot find column 'emoji' in INFORMATION_SCHEMA.")
        return
    dtype, collation = row
    print(f"  Current type: {dtype}  Collation: {collation}")
    if dtype.upper() == "NVARCHAR" and collation and "BIN2" in (collation or "").upper():
        print("  Column is already NVARCHAR + BIN2 collation. Running corrupted-row cleanup only...")
        _force_clean_corrupted(engine, q)
        return
    if dtype.upper() == "NVARCHAR":
        print(f"  Column is NVARCHAR but collation '{collation}' treats all emoji as equal.")
        print(f"  Applying BIN2 collation fix...")
    else:
        print(f"  Column is {dtype} — converting to NVARCHAR + BIN2...")

    # Step 1a: drop as key constraint
    print(f"\n  Step 1a: Drop [{idx_name}] as key constraint...")
    try:
        with engine.begin() as conn:
            exists = conn.execute(text(
                "SELECT name FROM sys.key_constraints "
                "WHERE name = :n AND parent_object_id = OBJECT_ID(:t)"
            ), {"n": idx_name, "t": table_name}).fetchone()
            if exists:
                conn.execute(text(f"ALTER TABLE {q} DROP CONSTRAINT [{idx_name}]"))
                print(f"    Dropped key constraint [{idx_name}]")
            else:
                print(f"    Not found as key constraint — skipping.")
    except Exception as exc:
        print(f"    FAILED: {exc}")
        return

    # Step 1b: drop as standalone index
    print(f"\n  Step 1b: Drop [{idx_name}] as standalone index...")
    try:
        with engine.begin() as conn:
            exists = conn.execute(text(
                "SELECT name FROM sys.indexes "
                "WHERE name = :n AND object_id = OBJECT_ID(:t) AND is_unique_constraint = 0"
            ), {"n": idx_name, "t": table_name}).fetchone()
            if exists:
                conn.execute(text(f"DROP INDEX [{idx_name}] ON {q}"))
                print(f"    Dropped index [{idx_name}]")
            else:
                print(f"    Not found as standalone index — skipping.")
    except Exception as exc:
        print(f"    FAILED: {exc}")
        return

    # Check for any remaining indexes on emoji column
    print(f"\n  Checking for any remaining indexes referencing emoji column...")
    with engine.connect() as conn:
        remaining = conn.execute(text(
            "SELECT i.name FROM sys.indexes i "
            "JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id "
            "JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id "
            "WHERE i.object_id = OBJECT_ID(N'review_reactions') AND c.name = 'emoji' "
            "AND i.name IS NOT NULL"
        )).fetchall()
    if remaining:
        print(f"  WARNING: Still have indexes on emoji: {[r[0] for r in remaining]}")
        print(f"  The ALTER COLUMN may still fail.")
    else:
        print(f"    No remaining indexes on emoji. Proceeding.")

    # Step 2: ALTER COLUMN with BIN2 collation for exact emoji comparison
    print(f"\n  Step 2: ALTER COLUMN emoji → NVARCHAR(32) COLLATE Latin1_General_BIN2...")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                f"ALTER TABLE {q} ALTER COLUMN [emoji] "
                f"NVARCHAR(32) COLLATE Latin1_General_BIN2 NOT NULL"
            ))
        print(f"    SUCCESS: Column is now NVARCHAR(32) COLLATE Latin1_General_BIN2.")
    except Exception as exc:
        print(f"    FAILED: {exc}")
        return

    # Step 3: recreate index
    print(f"\n  Step 3: Recreate unique index [{idx_name}]...")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                f"IF NOT EXISTS ("
                f"  SELECT 1 FROM sys.indexes WHERE name = '{idx_name}' AND object_id = OBJECT_ID(N'{table_name}')"
                f") CREATE UNIQUE NONCLUSTERED INDEX [{idx_name}] ON {q} (user_id, song_review_id, emoji)"
            ))
        print(f"    SUCCESS.")
    except Exception as exc:
        print(f"    WARNING: Could not recreate index: {exc}")

    # Step 4: clean corrupted rows
    print(f"\n  Step 4: Delete corrupted '?' rows...")
    _force_clean_corrupted(engine, q)

    print(f"\n  Done. Emoji reactions should now work correctly.")
    print(f"  Restart the app if it is currently running.")


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
            elif choice == "9":
                clear_review_reactions()
            elif choice == "a":
                diagnose_emoji_column()
            elif choice == "b":
                force_fix_emoji_column()
            elif choice == "0":
                print("\n  Goodbye.\n")
                sys.exit(0)
            else:
                print("  Invalid option.")


if __name__ == "__main__":
    main()
