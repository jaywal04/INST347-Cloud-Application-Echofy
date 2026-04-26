"""Direct messages between accepted friends."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from app.database import db
from app.models import DirectMessage, FriendRequest, User, utcnow_naive

messages_bp = Blueprint("messages", __name__)


def _friend_user(me_id: int, friend_id: int) -> User | None:
    if me_id == friend_id:
        return None
    relationship = FriendRequest.query.filter(
        FriendRequest.status == "accepted",
        or_(
            and_(FriendRequest.from_user_id == me_id, FriendRequest.to_user_id == friend_id),
            and_(FriendRequest.from_user_id == friend_id, FriendRequest.to_user_id == me_id),
        ),
    ).first()
    if not relationship:
        return None
    return db.session.get(User, friend_id)


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "profile_image_url": user.profile_image_url,
    }


def _conversation_query(me_id: int, friend_id: int):
    return DirectMessage.query.filter(
        or_(
            and_(DirectMessage.sender_id == me_id, DirectMessage.recipient_id == friend_id),
            and_(DirectMessage.sender_id == friend_id, DirectMessage.recipient_id == me_id),
        )
    )


@messages_bp.get("/api/messages/threads")
@login_required
def list_threads():
    me_id = current_user.id
    rows = FriendRequest.query.filter(
        FriendRequest.status == "accepted",
        or_(FriendRequest.from_user_id == me_id, FriendRequest.to_user_id == me_id),
    ).all()

    threads = []
    for row in rows:
        friend = row.from_user if row.to_user_id == me_id else row.to_user
        latest = (
            _conversation_query(me_id, friend.id)
            .order_by(DirectMessage.created_at.desc(), DirectMessage.id.desc())
            .first()
        )
        unread_count = DirectMessage.query.filter_by(
            sender_id=friend.id,
            recipient_id=me_id,
            read_at=None,
        ).count()
        latest_preview = ""
        latest_shared = None
        latest_at = None
        if latest:
            latest_preview = latest.text or ""
            latest_shared = latest.shared_item_dict()
            latest_at = latest.created_at.isoformat() if latest.created_at else None
        threads.append(
            {
                "friend": _user_summary(friend),
                "latest_message": latest_preview,
                "latest_shared_item": latest_shared,
                "latest_at": latest_at,
                "unread_count": unread_count,
            }
        )

    threads.sort(
        key=lambda item: (
            item["latest_at"] is None,
            item["latest_at"] or "",
            item["friend"]["username"].lower(),
        ),
        reverse=True,
    )
    return jsonify(ok=True, threads=threads)


@messages_bp.get("/api/messages/conversations/<int:friend_id>")
@login_required
def get_conversation(friend_id: int):
    me_id = current_user.id
    friend = _friend_user(me_id, friend_id)
    if not friend:
        return jsonify(ok=False, errors=["You can only message accepted friends."]), 403

    messages = (
        _conversation_query(me_id, friend_id)
        .order_by(DirectMessage.created_at.asc(), DirectMessage.id.asc())
        .limit(200)
        .all()
    )

    unread = [
        message
        for message in messages
        if message.recipient_id == me_id and message.read_at is None
    ]
    if unread:
        now = utcnow_naive()
        for message in unread:
            message.read_at = now
        db.session.commit()

    return jsonify(
        ok=True,
        friend=_user_summary(friend),
        messages=[message.to_dict(viewer_id=me_id) for message in messages],
    )


@messages_bp.post("/api/messages/conversations/<int:friend_id>")
@login_required
def send_message(friend_id: int):
    me_id = current_user.id
    friend = _friend_user(me_id, friend_id)
    if not friend:
        return jsonify(ok=False, errors=["You can only message accepted friends."]), 403

    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    shared_item = data.get("shared_item") if isinstance(data.get("shared_item"), dict) else None

    if not text and not shared_item:
        return jsonify(ok=False, errors=["Write a message or share a saved song."]), 400

    message = DirectMessage(
        sender_id=me_id,
        recipient_id=friend_id,
        text=text or None,
    )

    if shared_item:
        artists = shared_item.get("artists") or []
        if not isinstance(artists, list):
            artists = []
        message.shared_item_key = str(shared_item.get("item_key") or "")[:1024] or None
        message.shared_item_type = str(shared_item.get("type") or "track")[:20]
        message.shared_name = str(shared_item.get("name") or "")[:255] or None
        message.shared_artists = ", ".join(
            [str(artist).strip()[:120] for artist in artists if str(artist).strip()]
        )[:500] or None
        message.shared_album = str(shared_item.get("album") or "")[:255] or None
        message.shared_image_url = str(shared_item.get("image") or "")[:2048] or None
        message.shared_spotify_url = str(shared_item.get("url") or "")[:2048] or None

    db.session.add(message)
    db.session.commit()
    return jsonify(ok=True, message=message.to_dict(viewer_id=me_id))
