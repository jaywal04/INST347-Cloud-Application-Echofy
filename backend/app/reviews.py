"""Song review API routes."""

from __future__ import annotations

import hashlib
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.database import db
from app.models import SongReview, User, utcnow_naive


reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")


def _clean_string(value, max_len: int, default: str = "") -> str:
    if value is None:
        value = default
    value = str(value).strip()
    return value[:max_len]


def _item_key(item: dict) -> str:
    artists = item.get("artists") or []
    if not isinstance(artists, list):
        artists = [artists]
    return "|".join(
        [
            _clean_string(item.get("type"), 20, "track") or "track",
            _clean_string(item.get("url"), 2048),
            _clean_string(item.get("name"), 255),
            ",".join(_clean_string(a, 120) for a in artists),
            _clean_string(item.get("album"), 255),
        ]
    )


def _hash_key(item_key: str) -> str:
    return hashlib.sha256(item_key.encode("utf-8")).hexdigest()


@reviews_bp.get("/recent")
def recent_reviews():
    rows = (
        db.session.query(SongReview, User)
        .join(User, SongReview.user_id == User.id)
        .order_by(SongReview.updated_at.desc())
        .limit(10)
        .all()
    )
    result = []
    for review, user in rows:
        d = review.to_dict()
        d["username"] = user.username
        result.append(d)
    return jsonify(ok=True, reviews=result)


@reviews_bp.get("")
@login_required
def list_reviews():
    reviews = (
        SongReview.query.filter_by(user_id=current_user.id)
        .order_by(SongReview.updated_at.desc())
        .limit(200)
        .all()
    )
    return jsonify(ok=True, reviews=[review.to_dict() for review in reviews])


@reviews_bp.post("")
@login_required
def upsert_review():
    data = request.get_json(silent=True) or {}
    item = data.get("item") or {}
    if not isinstance(item, dict):
        return jsonify(ok=False, errors=["Song data is required."]), 400

    name = _clean_string(item.get("name"), 255)
    if not name:
        return jsonify(ok=False, errors=["Song name is required."]), 400

    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        return jsonify(ok=False, errors=["Rating must be a number from 1 to 5."]), 400

    if rating < 1 or rating > 5:
        return jsonify(ok=False, errors=["Rating must be from 1 to 5."]), 400

    text = _clean_string(data.get("text"), 280)
    item_key = _clean_string(data.get("item_key"), 1024) or _item_key(item)
    item_hash = _hash_key(item_key)
    artists = item.get("artists") or []
    if not isinstance(artists, list):
        artists = [artists]

    review = SongReview.query.filter_by(
        user_id=current_user.id,
        item_hash=item_hash,
    ).first()
    if review is None:
        review = SongReview(user_id=current_user.id, item_hash=item_hash, item_key=item_key)
        db.session.add(review)

    review.item_key = item_key
    review.item_type = _clean_string(item.get("type"), 20, "track") or "track"
    review.name = name
    review.artists = _clean_string(", ".join(_clean_string(a, 120) for a in artists), 500)
    review.album = _clean_string(item.get("album"), 255)
    review.image_url = _clean_string(item.get("image"), 2048)
    review.spotify_url = _clean_string(item.get("url"), 2048)
    review.rating = rating
    review.text = text
    review.updated_at = utcnow_naive()

    db.session.commit()
    return jsonify(ok=True, review=review.to_dict())
