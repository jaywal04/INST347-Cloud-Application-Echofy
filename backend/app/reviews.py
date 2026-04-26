"""Song review API routes."""

from __future__ import annotations

import hashlib
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.database import db
from app.models import SavedSpotifyItem, SongReview, User, utcnow_naive


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


def _avatar_text(username: str) -> str:
    letters = [chunk[:1].upper() for chunk in str(username or "").strip().split("_") if chunk[:1]]
    if not letters:
        return "EC"
    return "".join(letters[:2])


@reviews_bp.get("/home")
def homepage_reviews():
    top_items_rows = (
        db.session.query(
            SongReview.item_hash,
            SongReview.item_key,
            SongReview.item_type,
            SongReview.name,
            SongReview.artists,
            SongReview.album,
            SongReview.image_url,
            SongReview.spotify_url,
            func.count(SongReview.id).label("review_count"),
            func.avg(SongReview.rating).label("avg_rating"),
            func.max(SongReview.updated_at).label("last_activity"),
        )
        .join(User, User.id == SongReview.user_id)
        .filter(User.profile_public.is_(True), User.show_reviews.is_(True))
        .group_by(
            SongReview.item_hash,
            SongReview.item_key,
            SongReview.item_type,
            SongReview.name,
            SongReview.artists,
            SongReview.album,
            SongReview.image_url,
            SongReview.spotify_url,
        )
        .order_by(func.count(SongReview.id).desc(), func.max(SongReview.updated_at).desc())
        .limit(6)
        .all()
    )

    recent_rows = (
        db.session.query(SongReview, User.username)
        .join(User, User.id == SongReview.user_id)
        .filter(User.profile_public.is_(True), User.show_reviews.is_(True))
        .order_by(SongReview.updated_at.desc())
        .limit(5)
        .all()
    )

    ratings_logged = (
        db.session.query(func.count(SongReview.id))
        .join(User, User.id == SongReview.user_id)
        .filter(User.profile_public.is_(True), User.show_reviews.is_(True))
        .scalar()
        or 0
    )
    reviews_written = (
        db.session.query(func.count(SongReview.id))
        .join(User, User.id == SongReview.user_id)
        .filter(
            User.profile_public.is_(True),
            User.show_reviews.is_(True),
            SongReview.text.isnot(None),
            SongReview.text != "",
        )
        .scalar()
        or 0
    )
    public_members = User.query.filter(User.profile_public.is_(True)).count()

    top_items = [
        {
            "item_key": row.item_key,
            "item": {
                "type": row.item_type,
                "name": row.name,
                "artists": [a.strip() for a in (row.artists or "").split(",") if a.strip()],
                "album": row.album or "",
                "image": row.image_url or "",
                "url": row.spotify_url or "",
            },
            "review_count": int(row.review_count or 0),
            "avg_rating": round(float(row.avg_rating or 0), 1),
            "updated_at": row.last_activity.isoformat() if row.last_activity else None,
        }
        for row in top_items_rows
    ]

    recent_reviews = []
    for review, username in recent_rows:
        payload = review.to_dict()
        payload["username"] = username
        payload["avatar"] = _avatar_text(username)
        recent_reviews.append(payload)

    return jsonify(
        ok=True,
        top_items=top_items,
        recent_reviews=recent_reviews,
        stats={
            "ratings_logged": int(ratings_logged),
            "reviews_written": int(reviews_written),
            "public_members": int(public_members),
        },
    )


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


@reviews_bp.get("/saved")
@login_required
def list_saved_tracks():
    saved_items = (
        SavedSpotifyItem.query.filter_by(user_id=current_user.id, item_type="track")
        .order_by(SavedSpotifyItem.updated_at.desc())
        .limit(100)
        .all()
    )
    return jsonify(ok=True, items=[saved.to_dict() for saved in saved_items])


@reviews_bp.post("/saved")
@login_required
def save_track():
    data = request.get_json(silent=True) or {}
    item = data.get("item") or {}
    if not isinstance(item, dict):
        return jsonify(ok=False, errors=["Song data is required."]), 400

    item_type = _clean_string(item.get("type"), 20, "track") or "track"
    if item_type != "track":
        return jsonify(ok=False, errors=["Only tracks can be saved to Your Echo."]), 400

    name = _clean_string(item.get("name"), 255)
    if not name:
        return jsonify(ok=False, errors=["Song name is required."]), 400

    item_key = _clean_string(data.get("item_key"), 1024) or _item_key(item)
    item_hash = _hash_key(item_key)
    artists = item.get("artists") or []
    if not isinstance(artists, list):
        artists = [artists]

    saved = SavedSpotifyItem.query.filter_by(
        user_id=current_user.id,
        item_hash=item_hash,
    ).first()
    if saved is None:
        saved = SavedSpotifyItem(user_id=current_user.id, item_hash=item_hash, item_key=item_key)
        db.session.add(saved)

    saved.item_key = item_key
    saved.item_type = item_type
    saved.name = name
    saved.artists = _clean_string(", ".join(_clean_string(a, 120) for a in artists), 500)
    saved.album = _clean_string(item.get("album"), 255)
    saved.image_url = _clean_string(item.get("image"), 2048)
    saved.spotify_url = _clean_string(item.get("url"), 2048)
    saved.updated_at = utcnow_naive()

    db.session.commit()
    return jsonify(ok=True, item=saved.to_dict())


@reviews_bp.delete("/saved")
@login_required
def delete_saved_track():
    data = request.get_json(silent=True) or {}
    item_key = _clean_string(data.get("item_key"), 1024)
    if not item_key:
        return jsonify(ok=False, errors=["Item key is required."]), 400

    item_hash = _hash_key(item_key)
    saved = SavedSpotifyItem.query.filter_by(
        user_id=current_user.id,
        item_hash=item_hash,
    ).first()
    if saved is None:
        return jsonify(ok=True)

    db.session.delete(saved)
    db.session.commit()
    return jsonify(ok=True)


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
