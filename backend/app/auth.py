"""Authentication routes — signup, login, logout, session check."""

from __future__ import annotations

import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.database import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8


@auth_bp.post("/api/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirmPassword") or ""
    accepted_terms = bool(data.get("acceptedTerms"))

    errors = []

    if not _EMAIL_RE.match(email):
        errors.append("A valid email is required.")
    if not _USERNAME_RE.match(username):
        errors.append("Username must be 3-30 characters (letters, numbers, underscores).")
    if len(password) < _MIN_PASSWORD_LEN:
        errors.append(f"Password must be at least {_MIN_PASSWORD_LEN} characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    if not accepted_terms:
        errors.append("You must accept the Terms of Service.")

    if errors:
        return jsonify(ok=False, errors=errors), 400

    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify(ok=False, errors=["Email or username is already taken."]), 409

    user = User(username=username, email=email, accepted_terms=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify(ok=True, user={"id": user.id, "username": user.username}), 201


@auth_bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(ok=False, errors=["Username and password are required."]), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify(ok=False, errors=["Invalid username or password."]), 401

    login_user(user)
    return jsonify(ok=True, user={"id": user.id, "username": user.username}), 200


@auth_bp.post("/api/auth/logout")
@login_required
def logout():
    logout_user()
    return jsonify(ok=True), 200


@auth_bp.get("/api/auth/me")
def me():
    if current_user.is_authenticated:
        return jsonify(
            authenticated=True,
            user={"id": current_user.id, "username": current_user.username},
        )
    return jsonify(authenticated=False), 200
