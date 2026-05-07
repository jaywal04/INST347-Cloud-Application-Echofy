"""Direct messages between accepted friends."""

from __future__ import annotations

import json
import threading

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import and_, or_
from sqlalchemy.exc import DBAPIError, OperationalError

from app.blob_storage import signed_profile_image_url
from app.database import db
from app.models import DirectMessage, FriendRequest, User

messages_bp = Blueprint("messages", __name__)
_schema_ready = False
_schema_ready_lock = threading.Lock()


def _ensure_messages_schema_ready(force: bool = False) -> None:
    """Best-effort guard for legacy DBs where DM table/columns may be missing."""
    global _schema_ready
    if _schema_ready and not force:
        return
    with _schema_ready_lock:
        if _schema_ready and not force:
            return
        db.create_all()
        from app.schema_sync import ensure_model_table_columns

        ensure_model_table_columns(db.engine)
        _schema_ready = True


def _with_schema_retry(run_query):
    try:
        _ensure_messages_schema_ready()
        return run_query()
    except (OperationalError, DBAPIError):
        _ensure_messages_schema_ready(force=True)
        return run_query()


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


def _friend_ids(me_id: int) -> list[int]:
    rows = FriendRequest.query.filter(
        FriendRequest.status == "accepted",
        or_(FriendRequest.from_user_id == me_id, FriendRequest.to_user_id == me_id),
    ).all()
    return [
        r.from_user_id if r.to_user_id == me_id else r.to_user_id
        for r in rows
    ]


def _message_dict(msg: DirectMessage, me_id: int) -> dict:
    shared = None
    if msg.shared_item_json:
        try:
            shared = json.loads(msg.shared_item_json)
        except (ValueError, TypeError):
            shared = None
    return {
        "id": msg.id,
        "is_mine": msg.sender_id == me_id,
        "text": msg.text or "",
        "shared_item": shared,
        "read": msg.read,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@messages_bp.get("/api/messages/threads")
@login_required
def list_threads():
    def _run():
        me_id = current_user.id
        friend_id_list = _friend_ids(me_id)

        threads = []
        for fid in friend_id_list:
            friend = db.session.get(User, fid)
            if not friend:
                continue

            latest = (
                DirectMessage.query.filter(
                    or_(
                        and_(DirectMessage.sender_id == me_id, DirectMessage.recipient_id == fid),
                        and_(DirectMessage.sender_id == fid, DirectMessage.recipient_id == me_id),
                    )
                )
                .order_by(DirectMessage.created_at.desc())
                .first()
            )

            unread_count = DirectMessage.query.filter_by(
                sender_id=fid, recipient_id=me_id, read=False
            ).count()

            shared_item = None
            if latest and latest.shared_item_json:
                try:
                    shared_item = json.loads(latest.shared_item_json)
                except (ValueError, TypeError):
                    shared_item = None

            threads.append(
                {
                    "friend": {
                        "id": friend.id,
                        "username": friend.username,
                        "profile_image_url": signed_profile_image_url(friend.profile_image_url),
                    },
                    "latest_at": latest.created_at.isoformat()
                    if latest and latest.created_at
                    else None,
                    "latest_message": latest.text if latest and latest.text else None,
                    "latest_shared_item": shared_item,
                    "unread_count": unread_count,
                }
            )

        threads.sort(key=lambda t: t["latest_at"] or "", reverse=True)
        return jsonify(ok=True, threads=threads)

    return _with_schema_retry(_run)


@messages_bp.get("/api/messages/conversations/<int:friend_id>")
@login_required
def get_conversation(friend_id: int):
    def _run():
        me_id = current_user.id
        if not _are_friends(me_id, friend_id):
            return jsonify(ok=False, errors=["Not friends with this user."]), 403

        friend = db.session.get(User, friend_id)
        if not friend:
            return jsonify(ok=False, errors=["User not found."]), 404

        DirectMessage.query.filter_by(
            sender_id=friend_id, recipient_id=me_id, read=False
        ).update({"read": True})
        db.session.commit()

        messages = (
            DirectMessage.query.filter(
                or_(
                    and_(DirectMessage.sender_id == me_id, DirectMessage.recipient_id == friend_id),
                    and_(DirectMessage.sender_id == friend_id, DirectMessage.recipient_id == me_id),
                )
            )
            .order_by(DirectMessage.created_at.asc())
            .limit(200)
            .all()
        )

        return jsonify(
            ok=True,
            friend={
                "id": friend.id,
                "username": friend.username,
                "profile_image_url": signed_profile_image_url(friend.profile_image_url),
            },
            messages=[_message_dict(m, me_id) for m in messages],
        )

    return _with_schema_retry(_run)


@messages_bp.post("/api/messages/conversations/<int:friend_id>")
@login_required
def send_message(friend_id: int):
    def _run():
        me_id = current_user.id
        if not _are_friends(me_id, friend_id):
            return jsonify(ok=False, errors=["Not friends with this user."]), 403

        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        shared_item = data.get("shared_item")

        if not text and not shared_item:
            return jsonify(ok=False, errors=["Message text or a shared item is required."]), 400
        if len(text) > 2000:
            return jsonify(ok=False, errors=["Message is too long (max 2000 characters)."]), 400

        shared_item_json = None
        if shared_item and isinstance(shared_item, dict):
            try:
                shared_item_json = json.dumps(shared_item)
            except (TypeError, ValueError):
                shared_item_json = None

        msg = DirectMessage(
            sender_id=me_id,
            recipient_id=friend_id,
            text=text or None,
            shared_item_json=shared_item_json,
            read=False,
        )
        db.session.add(msg)
        db.session.commit()

        return jsonify(ok=True, message=_message_dict(msg, me_id))

    return _with_schema_retry(_run)


@messages_bp.get("/api/messages/unread-count")
@login_required
def unread_count():
    def _run():
        me_id = current_user.id
        count = DirectMessage.query.filter_by(recipient_id=me_id, read=False).count()
        return jsonify(ok=True, count=count)

    return _with_schema_retry(_run)
