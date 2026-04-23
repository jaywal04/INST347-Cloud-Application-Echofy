"""Friends list, friend requests, and user search."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_

from app.database import db
from app.models import FriendRequest, User, utcnow_naive

friends_bp = Blueprint("friends", __name__)


def _now():
    return utcnow_naive()


def _are_friends(a_id: int, b_id: int) -> bool:
    if a_id == b_id:
        return False
    return (
        FriendRequest.query.filter(
            FriendRequest.status == "accepted",
            or_(
                and_(FriendRequest.from_user_id == a_id, FriendRequest.to_user_id == b_id),
                and_(FriendRequest.from_user_id == b_id, FriendRequest.to_user_id == a_id),
            ),
        ).first()
        is not None
    )


def _related_user_ids_for_search(me_id: int) -> set[int]:
    """Users already pending or accepted with me — hide from search."""
    rows = FriendRequest.query.filter(
        or_(FriendRequest.from_user_id == me_id, FriendRequest.to_user_id == me_id),
        FriendRequest.status.in_(("pending", "accepted")),
    ).all()
    out: set[int] = set()
    for r in rows:
        out.add(r.to_user_id if r.from_user_id == me_id else r.from_user_id)
    return out


def _user_summary(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "profile_image_url": u.profile_image_url,
    }


@friends_bp.get("/api/users/<int:user_id>/profile")
@login_required
def public_profile(user_id: int):
    """Return a user's public profile, respecting their privacy settings."""
    user = db.session.get(User, user_id)
    if not user or not user.profile_public:
        return jsonify(ok=False, errors=["User not found or profile is private."]), 404

    profile = {
        "id": user.id,
        "username": user.username,
        "profile_image_url": user.profile_image_url,
    }

    if user.show_bio:
        profile["bio"] = user.bio
    if user.show_genre:
        profile["favorite_genre"] = user.favorite_genre

    return jsonify(ok=True, profile=profile)


@friends_bp.get("/api/users/search")
@login_required
def search_users():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify(ok=False, errors=["Search query must be at least 2 characters."]), 400

    me_id = current_user.id
    hide_ids = _related_user_ids_for_search(me_id)
    hide_ids.add(me_id)

    pattern = f"%{q}%"
    qry = User.query.filter(
        User.profile_public == True,
        User.username.ilike(pattern),
        ~User.id.in_(hide_ids),
    )
    users = qry.order_by(User.username).limit(20).all()

    return jsonify(
        ok=True,
        users=[{"id": u.id, "username": u.username} for u in users],
    )


@friends_bp.get("/api/friends")
@login_required
def list_friends():
    me_id = current_user.id
    rows = FriendRequest.query.filter(
        FriendRequest.status == "accepted",
        or_(FriendRequest.from_user_id == me_id, FriendRequest.to_user_id == me_id),
    ).all()
    friends = []
    for r in rows:
        other = r.from_user if r.to_user_id == me_id else r.to_user
        friends.append(_user_summary(other))
    friends.sort(key=lambda x: x["username"].lower())
    return jsonify(ok=True, friends=friends)


@friends_bp.get("/api/notifications/count")
@login_required
def notification_count():
    me_id = current_user.id
    count = FriendRequest.query.filter_by(to_user_id=me_id, status="pending").count()
    return jsonify(ok=True, count=count)


@friends_bp.get("/api/friends/requests/incoming")
@login_required
def incoming_requests():
    me_id = current_user.id
    rows = (
        FriendRequest.query.filter_by(to_user_id=me_id, status="pending")
        .order_by(FriendRequest.created_at.desc())
        .all()
    )
    return jsonify(
        ok=True,
        requests=[
            {
                "id": r.id,
                "from_user": {"id": r.from_user.id, "username": r.from_user.username},
            }
            for r in rows
        ],
    )


@friends_bp.get("/api/friends/requests/outgoing")
@login_required
def outgoing_requests():
    me_id = current_user.id
    rows = (
        FriendRequest.query.filter_by(from_user_id=me_id, status="pending")
        .order_by(FriendRequest.created_at.desc())
        .all()
    )
    return jsonify(
        ok=True,
        requests=[
            {
                "id": r.id,
                "to_user": {"id": r.to_user.id, "username": r.to_user.username},
            }
            for r in rows
        ],
    )


@friends_bp.post("/api/friends/requests")
@login_required
def create_friend_request():
    data = request.get_json(silent=True) or {}
    me_id = current_user.id
    target: User | None = None
    if data.get("user_id") is not None:
        try:
            uid = int(data["user_id"])
        except (TypeError, ValueError):
            return jsonify(ok=False, errors=["Invalid user_id."]), 400
        target = db.session.get(User, uid)
    else:
        username = (data.get("username") or "").strip()
        if not username:
            return jsonify(ok=False, errors=["username or user_id is required."]), 400
        target = User.query.filter(func.lower(User.username) == username.lower()).first()

    if not target:
        return jsonify(ok=False, errors=["User not found."]), 404
    if target.id == me_id:
        return jsonify(ok=False, errors=["You cannot add yourself as a friend."]), 400

    if _are_friends(me_id, target.id):
        return jsonify(ok=False, errors=["You are already friends with this user."]), 409

    # Reverse pending: B→A pending, A sends → accept
    reverse = FriendRequest.query.filter_by(
        from_user_id=target.id, to_user_id=me_id, status="pending"
    ).first()
    if reverse:
        reverse.status = "accepted"
        reverse.updated_at = _now()
        db.session.commit()
        return jsonify(ok=True, auto_accepted=True, message="You are now friends.")

    existing = FriendRequest.query.filter_by(from_user_id=me_id, to_user_id=target.id).first()
    if existing:
        if existing.status == "pending":
            return jsonify(ok=True, already_pending=True)
        if existing.status == "accepted":
            return jsonify(ok=False, errors=["You are already friends with this user."]), 409
        if existing.status == "declined":
            existing.status = "pending"
            existing.updated_at = _now()
            db.session.commit()
            return jsonify(ok=True, resent=True)

    fr = FriendRequest(from_user_id=me_id, to_user_id=target.id, status="pending")
    db.session.add(fr)
    db.session.commit()
    return jsonify(ok=True, request_id=fr.id)


@friends_bp.post("/api/friends/requests/<int:request_id>/accept")
@login_required
def accept_request(request_id: int):
    me_id = current_user.id
    fr = db.session.get(FriendRequest, request_id)
    if not fr or fr.to_user_id != me_id:
        return jsonify(ok=False, errors=["Request not found."]), 404
    if fr.status != "pending":
        return jsonify(ok=False, errors=["This request is no longer pending."]), 400
    fr.status = "accepted"
    fr.updated_at = _now()
    db.session.commit()
    return jsonify(ok=True)


@friends_bp.post("/api/friends/requests/<int:request_id>/decline")
@login_required
def decline_request(request_id: int):
    me_id = current_user.id
    fr = db.session.get(FriendRequest, request_id)
    if not fr or fr.to_user_id != me_id:
        return jsonify(ok=False, errors=["Request not found."]), 404
    if fr.status != "pending":
        return jsonify(ok=False, errors=["This request is no longer pending."]), 400
    fr.status = "declined"
    fr.updated_at = _now()
    db.session.commit()
    return jsonify(ok=True)
