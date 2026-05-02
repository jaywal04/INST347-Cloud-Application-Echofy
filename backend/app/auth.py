"""Authentication routes — signup, login, logout, session check."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from werkzeug.security import generate_password_hash

from app.blob_storage import (
    delete_blob_by_url,
    signed_profile_image_url,
    upload_profile_image,
)
from app.database import db
from app.email_service import send_verification_code
from app.models import FriendRequest, PendingVerification, ReviewLike, User, utcnow_naive

auth_bp = Blueprint("auth", __name__)

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")

# First URL segment for logged-in routes; static dirs — do not allow as usernames.
_RESERVED_USERNAMES = frozenset(
    {
        "login",
        "signup",
        "discover",
        "discovery",
        "dashboard",
        "friends",
        "profile",
        "notifications",
        "user",
        "review",
        "css",
        "js",
        "index",
        "api",
        "auth",
        "callback",
        "static",
        "assets",
        "fonts",
        "www",
    }
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8
_MAX_VERIFY_ATTEMPTS = 5


def _generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


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
    elif username.lower() in _RESERVED_USERNAMES:
        errors.append("That username is reserved. Please choose another.")
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

    # Clean up any old pending verifications for this email
    PendingVerification.query.filter_by(email=email, purpose="signup").delete()
    db.session.commit()

    code = _generate_code()
    pv = PendingVerification(
        email=email,
        code=code,
        purpose="signup",
        username=username,
        password_hash=generate_password_hash(password),
        expires_at=utcnow_naive() + timedelta(minutes=3),
    )
    db.session.add(pv)
    db.session.commit()

    if not send_verification_code(email, code, purpose="signup"):
        return jsonify(ok=False, errors=["Failed to send verification email. Please try again."]), 503

    return jsonify(ok=True, verify=True, email=email), 200


@auth_bp.post("/api/auth/verify-signup")
def verify_signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    if not email or not code:
        return jsonify(ok=False, errors=["Email and verification code are required."]), 400

    pv = PendingVerification.query.filter_by(
        email=email, purpose="signup"
    ).order_by(PendingVerification.created_at.desc()).first()

    if not pv:
        return jsonify(ok=False, errors=["No pending verification found. Please sign up again."]), 404

    if pv.is_expired():
        db.session.delete(pv)
        db.session.commit()
        return jsonify(ok=False, errors=["Verification code has expired. Please sign up again."]), 410

    if pv.attempts >= _MAX_VERIFY_ATTEMPTS:
        db.session.delete(pv)
        db.session.commit()
        return jsonify(ok=False, errors=["Too many incorrect attempts. Please sign up again."]), 429

    if pv.code != code:
        pv.attempts = (pv.attempts or 0) + 1
        db.session.commit()
        return jsonify(ok=False, errors=["Incorrect verification code."]), 400

    # Check again that email/username haven't been taken while waiting
    if User.query.filter((User.email == email) | (User.username == pv.username)).first():
        db.session.delete(pv)
        db.session.commit()
        return jsonify(ok=False, errors=["Email or username is already taken."]), 409

    if pv.username.lower() in _RESERVED_USERNAMES:
        db.session.delete(pv)
        db.session.commit()
        return jsonify(
            ok=False,
            errors=["That username is reserved. Please sign up again with a different username."],
        ), 400

    # Create the user
    user = User(username=pv.username, email=email, accepted_terms=True)
    user.password_hash = pv.password_hash
    db.session.add(user)
    db.session.delete(pv)
    db.session.commit()

    login_user(user)
    return jsonify(ok=True, user={"id": user.id, "username": user.username}), 201


@auth_bp.post("/api/auth/resend-code")
def resend_code():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    purpose = data.get("purpose") or "signup"

    if not email:
        return jsonify(ok=False, errors=["Email is required."]), 400

    # For delete purpose, only the authenticated user can resend to their own email
    if purpose == "delete":
        if not current_user.is_authenticated or current_user.email != email:
            return jsonify(ok=False, errors=["Unauthorized."]), 401

    pv = PendingVerification.query.filter_by(
        email=email, purpose=purpose
    ).order_by(PendingVerification.created_at.desc()).first()

    if not pv:
        # Don't reveal whether a pending verification exists
        return jsonify(ok=True), 200

    # Generate a new code and reset expiry, reset attempts
    code = _generate_code()
    pv.code = code
    pv.attempts = 0
    pv.expires_at = utcnow_naive() + timedelta(minutes=3)
    db.session.commit()

    if not send_verification_code(email, code, purpose=purpose):
        return jsonify(ok=False, errors=["Failed to send email. Please try again."]), 503

    return jsonify(ok=True), 200


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
    from flask import session as flask_session
    flask_session.pop("spotify_access_token", None)
    flask_session.pop("spotify_refresh_token", None)
    flask_session.pop("spotify_oauth_state", None)
    return jsonify(ok=True), 200


@auth_bp.get("/api/auth/me")
def me():
    if current_user.is_authenticated:
        return jsonify(
            authenticated=True,
            user={
                "id": current_user.id,
                "username": current_user.username,
                "profile_image_url": signed_profile_image_url(
                    current_user.profile_image_url
                ),
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
        "show_bio": u.show_bio,
        "show_genre": u.show_genre,
        "profile_image_url": signed_profile_image_url(u.profile_image_url),
    })


@auth_bp.put("/api/auth/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    u = current_user

    if "age" in data:
        age = data["age"]
        if age is not None:
            try:
                age = int(age)
            except (TypeError, ValueError):
                return jsonify(ok=False, errors=["Age must be a number."]), 400
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
    return jsonify(ok=True, profile_image_url=signed_profile_image_url(url))


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
    if "show_bio" in data:
        u.show_bio = bool(data["show_bio"])
    if "show_genre" in data:
        u.show_genre = bool(data["show_genre"])

    db.session.commit()
    return jsonify(ok=True)


@auth_bp.post("/api/auth/delete-request")
@login_required
def delete_request():
    """Step 1: Verify password, then send a deletion verification code to email."""
    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    if not password:
        return jsonify(ok=False, errors=["Password is required."]), 400

    if not current_user.check_password(password):
        return jsonify(ok=False, errors=["Incorrect password."]), 401

    email = current_user.email

    # Clean up old delete verifications for this user
    PendingVerification.query.filter_by(email=email, purpose="delete").delete()
    db.session.commit()

    code = _generate_code()
    pv = PendingVerification(
        email=email,
        code=code,
        purpose="delete",
        user_id=current_user.id,
        expires_at=utcnow_naive() + timedelta(minutes=3),
    )
    db.session.add(pv)
    db.session.commit()

    if not send_verification_code(email, code, purpose="delete"):
        return jsonify(ok=False, errors=["Failed to send verification email."]), 503

    return jsonify(ok=True, email=email), 200


@auth_bp.delete("/api/auth/account")
@login_required
def delete_account():
    """Step 2: Verify the 6-digit code and permanently delete the account."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    if not code:
        return jsonify(ok=False, errors=["Verification code is required."]), 400

    email = current_user.email
    pv = PendingVerification.query.filter_by(
        email=email, purpose="delete"
    ).order_by(PendingVerification.created_at.desc()).first()

    if not pv:
        return jsonify(ok=False, errors=["No pending deletion request. Please start over."]), 404

    if pv.is_expired():
        db.session.delete(pv)
        db.session.commit()
        return jsonify(ok=False, errors=["Verification code has expired. Please start over."]), 410

    if pv.attempts >= _MAX_VERIFY_ATTEMPTS:
        db.session.delete(pv)
        db.session.commit()
        return jsonify(ok=False, errors=["Too many incorrect attempts. Please start over."]), 429

    if pv.code != code:
        pv.attempts = (pv.attempts or 0) + 1
        db.session.commit()
        return jsonify(ok=False, errors=["Incorrect verification code."]), 400

    user = db.session.get(User, current_user.id)
    delete_blob_by_url(user.profile_image_url if user else None)
    FriendRequest.query.filter(
        or_(FriendRequest.from_user_id == user.id, FriendRequest.to_user_id == user.id)
    ).delete(synchronize_session=False)
    ReviewLike.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(pv)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    return jsonify(ok=True)
