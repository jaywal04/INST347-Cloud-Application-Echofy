"""Song review API routes."""

from __future__ import annotations

import hashlib

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import ReviewLike, SongReview, User, utcnow_naive


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


def _like_counts_subquery():
    return (
        db.session.query(
            ReviewLike.song_review_id.label("rid"),
            func.count(ReviewLike.id).label("cnt"),
        )
        .group_by(ReviewLike.song_review_id)
        .subquery()
    )


def _like_meta_for_reviews(review_ids: list[int], viewer_id: int | None) -> dict[int, dict]:
    if not review_ids:
        return {}
    rows = (
        db.session.query(ReviewLike.song_review_id, func.count(ReviewLike.id))
        .filter(ReviewLike.song_review_id.in_(review_ids))
        .group_by(ReviewLike.song_review_id)
        .all()
    )
    count_map = {int(sid): int(n) for sid, n in rows}
    liked: set[int] = set()
    if viewer_id is not None:
        liked = {
            int(r[0])
            for r in db.session.query(ReviewLike.song_review_id)
            .filter(
                ReviewLike.song_review_id.in_(review_ids),
                ReviewLike.user_id == viewer_id,
            )
            .all()
        }
    out: dict[int, dict] = {}
    for rid in review_ids:
        rid = int(rid)
        out[rid] = {
            "like_count": int(count_map.get(rid, 0)),
            "liked_by_me": rid in liked,
        }
    return out


def _apply_like_fields(d: dict, rid: int, meta: dict[int, dict]) -> None:
    m = meta.get(int(rid), {"like_count": 0, "liked_by_me": False})
    d["like_count"] = m["like_count"]
    d["liked_by_me"] = m["liked_by_me"]


def _browse_search_pattern(raw: str) -> str | None:
    """Substring match for name / artists / album / text; strip LIKE metacharacters."""
    s = (raw or "").strip()[:120]
    if not s:
        return None
    s = s.replace("\\", "").replace("%", "").replace("_", "").strip()
    if not s:
        return None
    return f"%{s}%"


@reviews_bp.get("/recent")
def recent_reviews():
    rows = (
        db.session.query(SongReview, User)
        .join(User, SongReview.user_id == User.id)
        .order_by(SongReview.updated_at.desc())
        .limit(10)
        .all()
    )
    ids = [r[0].id for r in rows]
    viewer_id = current_user.id if current_user.is_authenticated else None
    meta = _like_meta_for_reviews(ids, viewer_id)
    result = []
    for review, user in rows:
        d = review.to_dict()
        d["username"] = user.username
        _apply_like_fields(d, review.id, meta)
        result.append(d)
    return jsonify(ok=True, reviews=result)


@reviews_bp.get("/browse")
def browse_reviews():
    """Public list: sort and category filters over all users' reviews."""
    sort = (request.args.get("sort") or "top").strip().lower()
    if sort not in ("top", "recent", "oldest", "least"):
        sort = "top"
    category = (request.args.get("category") or "all").strip().lower()
    try:
        limit = min(100, max(1, int(request.args.get("limit", 50))))
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except (TypeError, ValueError):
        offset = 0

    q = db.session.query(SongReview, User).join(User, SongReview.user_id == User.id)
    lc = None
    if sort == "top":
        lc = _like_counts_subquery()
        q = q.outerjoin(lc, SongReview.id == lc.c.rid)

    if category == "tracks":
        q = q.filter(
            or_(
                SongReview.item_type.is_(None),
                SongReview.item_type == "",
                SongReview.item_type == "track",
            )
        )
    elif category == "albums":
        q = q.filter(SongReview.item_type == "album")
    elif category == "artists":
        q = q.filter(SongReview.item_type == "artist")
    elif category == "genres":
        q = q.filter(SongReview.item_type == "genre")

    search_pat = _browse_search_pattern(
        request.args.get("q") or request.args.get("search") or ""
    )
    if search_pat:
        q = q.filter(
            or_(
                SongReview.name.ilike(search_pat),
                SongReview.artists.ilike(search_pat),
                SongReview.album.ilike(search_pat),
                SongReview.text.ilike(search_pat),
            )
        )

    if sort == "recent":
        q = q.order_by(SongReview.updated_at.desc())
    elif sort == "oldest":
        q = q.order_by(SongReview.updated_at.asc())
    elif sort == "least":
        q = q.order_by(SongReview.rating.asc(), SongReview.updated_at.desc())
    else:
        # "top" = most community likes, then star rating, then recency
        q = q.order_by(
            func.coalesce(lc.c.cnt, 0).desc(),
            SongReview.rating.desc(),
            SongReview.updated_at.desc(),
        )

    rows = q.offset(offset).limit(limit).all()
    ids = [r[0].id for r in rows]
    viewer_id = current_user.id if current_user.is_authenticated else None
    meta = _like_meta_for_reviews(ids, viewer_id)
    result = []
    for review, user in rows:
        d = review.to_dict()
        d["username"] = user.username
        _apply_like_fields(d, review.id, meta)
        result.append(d)
    return jsonify(ok=True, reviews=result)


def _is_spotify_track_url(url: str) -> bool:
    u = (url or "").strip().lower()
    if "spotify:track:" in u.replace(" ", ""):
        return True
    return "open.spotify.com" in u and "/track/" in u


@reviews_bp.post("/for-item")
def reviews_for_item():
    """Public: all reviews for one catalog track (same item_hash as Discover)."""
    data = request.get_json(silent=True) or {}
    item = data.get("item") or {}
    if not isinstance(item, dict):
        return jsonify(ok=False, errors=["item is required."]), 400

    name = _clean_string(item.get("name"), 255)
    url = _clean_string(item.get("url"), 2048)
    if not name or not url:
        return jsonify(ok=False, errors=["item.name and item.url are required."]), 400

    itype = _clean_string(item.get("type"), 20, "track") or "track"
    if itype != "track":
        return jsonify(ok=False, errors=["Only track items are supported."]), 400

    if not _is_spotify_track_url(url):
        return jsonify(ok=False, errors=["item.url must be a Spotify track link."]), 400

    item_key = _item_key(item)
    item_hash = _hash_key(item_key)

    lc = _like_counts_subquery()
    rows = (
        db.session.query(SongReview, User)
        .join(User, SongReview.user_id == User.id)
        .outerjoin(lc, SongReview.id == lc.c.rid)
        .filter(SongReview.item_hash == item_hash)
        .order_by(
            func.coalesce(lc.c.cnt, 0).desc(),
            SongReview.rating.desc(),
            SongReview.updated_at.desc(),
        )
        .limit(100)
        .all()
    )
    ids = [r[0].id for r in rows]
    viewer_id = current_user.id if current_user.is_authenticated else None
    meta = _like_meta_for_reviews(ids, viewer_id)
    result = []
    for review, user in rows:
        d = review.to_dict()
        d["username"] = user.username
        _apply_like_fields(d, review.id, meta)
        result.append(d)

    artists = item.get("artists") or []
    if not isinstance(artists, list):
        artists = [artists]
    clean_item = {
        "type": "track",
        "name": name,
        "url": url,
        "artists": [_clean_string(a, 120) for a in artists if _clean_string(a, 120)],
        "album": _clean_string(item.get("album"), 255),
        "image": _clean_string(item.get("image"), 2048),
    }
    return jsonify(ok=True, reviews=result, item_key=item_key, item=clean_item)


@reviews_bp.post("/<int:review_id>/like")
@login_required
def like_review(review_id: int):
    review = db.session.get(SongReview, review_id)
    if review is None:
        return jsonify(ok=False, errors=["Review not found."]), 404
    if review.user_id == current_user.id:
        return jsonify(ok=False, errors=["You cannot like your own review."]), 400
    existing = ReviewLike.query.filter_by(
        user_id=current_user.id, song_review_id=review_id
    ).first()
    if existing is None:
        db.session.add(
            ReviewLike(user_id=current_user.id, song_review_id=review_id)
        )
        try:
            db.session.commit()
        except IntegrityError:
            # Concurrent like or DB unique enforced while row already existed
            db.session.rollback()
    cnt = (
        db.session.query(func.count(ReviewLike.id))
        .filter(ReviewLike.song_review_id == review_id)
        .scalar()
    )
    return jsonify(ok=True, like_count=int(cnt or 0), liked_by_me=True)


@reviews_bp.delete("/<int:review_id>/like")
@login_required
def unlike_review(review_id: int):
    review = db.session.get(SongReview, review_id)
    if review is None:
        return jsonify(ok=False, errors=["Review not found."]), 404
    ReviewLike.query.filter_by(
        user_id=current_user.id, song_review_id=review_id
    ).delete()
    db.session.commit()
    cnt = (
        db.session.query(func.count(ReviewLike.id))
        .filter(ReviewLike.song_review_id == review_id)
        .scalar()
    )
    return jsonify(ok=True, like_count=int(cnt or 0), liked_by_me=False)


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
