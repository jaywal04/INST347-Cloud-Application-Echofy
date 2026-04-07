"""Authentication routes — signup, login, logout, session check."""

from __future__ import annotations

import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from app.blob_storage import delete_blob_by_url, upload_profile_image
from app.database import db
from app.models import FriendRequest, User

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
            user={
                "id": current_user.id,
                "username": current_user.username,
                "profile_image_url": current_user.profile_image_url,
            },
        )
    return jsonify(authenticated=False), 200


@auth_bp.get("/api/auth/profile")
@login_required
def get_profile():
    u = current_user
    return jsonify(ok=True, profile={
        "username": u.username,
        "email": u.email,
        "age": u.age,
        "sex": u.sex,
        "bio": u.bio,
        "location": u.location,
        "favorite_genre": u.favorite_genre,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "profile_public": u.profile_public,
        "show_listening_history": u.show_listening_history,
        "show_reviews": u.show_reviews,
        "profile_image_url": u.profile_image_url,
    })


@auth_bp.put("/api/auth/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    u = current_user

    if "age" in data:
        age = data["age"]
        if age is not None:
            age = int(age)
            if age < 13 or age > 120:
                return jsonify(ok=False, errors=["Age must be between 13 and 120."]), 400
        u.age = age

    if "sex" in data or "gender" in data:
        allowed = ("male", "female", "non-binary", "prefer not to say", "")
        raw = data["sex"] if "sex" in data else data.get("gender")
        val = (raw or "").strip().lower()
        if val and val not in allowed:
            return jsonify(ok=False, errors=["Invalid sex value."]), 400
        u.sex = val or None

    if "bio" in data:
        bio = (data["bio"] or "").strip()
        if len(bio) > 500:
            return jsonify(ok=False, errors=["Bio must be 500 characters or fewer."]), 400
        u.bio = bio or None

    if "location" in data:
        u.location = (data["location"] or "").strip()[:100] or None

    if "favorite_genre" in data:
        u.favorite_genre = (data["favorite_genre"] or "").strip()[:50] or None

    db.session.commit()
    return jsonify(ok=True)


@auth_bp.post("/api/auth/profile/photo")
@login_required
def upload_profile_photo():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(ok=False, errors=["No file uploaded (use form field \"file\")."]), 400

    u = db.session.get(User, current_user.id)
    if not u:
        return jsonify(ok=False, errors=["User not found."]), 404

    old_url = u.profile_image_url
    url, err = upload_profile_image(u.id, f)
    if err:
        return jsonify(ok=False, errors=[err]), 503

    u.profile_image_url = url
    db.session.commit()
    delete_blob_by_url(old_url)
    return jsonify(ok=True, profile_image_url=url)


@auth_bp.delete("/api/auth/profile/photo")
@login_required
def delete_profile_photo():
    u = db.session.get(User, current_user.id)
    if not u:
        return jsonify(ok=False, errors=["User not found."]), 404

    delete_blob_by_url(u.profile_image_url)
    u.profile_image_url = None
    db.session.commit()
    return jsonify(ok=True)


@auth_bp.put("/api/auth/privacy")
@login_required
def update_privacy():
    data = request.get_json(silent=True) or {}
    u = current_user

    if "profile_public" in data:
        u.profile_public = bool(data["profile_public"])
    if "show_listening_history" in data:
        u.show_listening_history = bool(data["show_listening_history"])
    if "show_reviews" in data:
        u.show_reviews = bool(data["show_reviews"])

    db.session.commit()
    return jsonify(ok=True)


@auth_bp.delete("/api/auth/account")
@login_required
def delete_account():
    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    if not password:
        return jsonify(ok=False, errors=["Password is required to delete your account."]), 400

    if not current_user.check_password(password):
        return jsonify(ok=False, errors=["Incorrect password."]), 401

    user = db.session.get(User, current_user.id)
    delete_blob_by_url(user.profile_image_url if user else None)
    FriendRequest.query.filter(
        or_(FriendRequest.from_user_id == user.id, FriendRequest.to_user_id == user.id)
    ).delete(synchronize_session=False)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    return jsonify(ok=True)
