"""Database models."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db


class PendingVerification(db.Model):
    """Stores 6-digit verification codes for signup and account deletion."""

    __tablename__ = "pending_verifications"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), nullable=False, default="signup")  # signup | delete
    # For signup: store the registration payload so we can create the user on verify
    username = db.Column(db.String(80), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)  # for delete purpose
    attempts = db.Column(db.Integer, default=0, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp


class FriendRequest(db.Model):
    """Directed friend request: from_user → to_user. When accepted, the row stays as status accepted."""

    __tablename__ = "friend_requests"
    __table_args__ = (
        db.UniqueConstraint("from_user_id", "to_user_id", name="uq_friend_requests_from_to"),
    )

    id = db.Column(db.Integer, primary_key=True)
    # SQL Server rejects two ON DELETE CASCADE FKs from this table to the same parent (error 1785).
    from_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="NO ACTION"), nullable=False, index=True
    )
    to_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="NO ACTION"), nullable=False, index=True
    )
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    from_user = db.relationship("User", foreign_keys=[from_user_id], backref=db.backref("friend_requests_sent", lazy="dynamic"))
    to_user = db.relationship("User", foreign_keys=[to_user_id], backref=db.backref("friend_requests_received", lazy="dynamic"))


class SongReview(db.Model):
    """A user's Spotify rating/review saved in the app database."""

    __tablename__ = "song_reviews"
    __table_args__ = (
        db.UniqueConstraint("user_id", "item_hash", name="uq_song_reviews_user_item"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_hash = db.Column(db.String(64), nullable=False, index=True)
    item_key = db.Column(db.String(1024), nullable=False)
    item_type = db.Column(db.String(20), nullable=False, default="track")
    name = db.Column(db.String(255), nullable=False)
    artists = db.Column(db.String(500), nullable=True)
    album = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(2048), nullable=True)
    spotify_url = db.Column(db.String(2048), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String(280), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("song_reviews", lazy="dynamic"))

    def to_dict(self) -> dict:
        artists = [a.strip() for a in (self.artists or "").split(",") if a.strip()]
        return {
            "id": self.id,
            "item_key": self.item_key,
            "rating": self.rating,
            "text": self.text or "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "item": {
                "type": self.item_type,
                "name": self.name,
                "artists": artists,
                "album": self.album or "",
                "image": self.image_url or "",
                "url": self.spotify_url or "",
            },
        }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    accepted_terms = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    age = db.Column(db.Integer, nullable=True)
    sex = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    favorite_genre = db.Column(db.String(50), nullable=True)
    profile_public = db.Column(db.Boolean, default=True, nullable=False)
    show_listening_history = db.Column(db.Boolean, default=True, nullable=False)
    show_reviews = db.Column(db.Boolean, default=True, nullable=False)
    show_bio = db.Column(db.Boolean, default=True, nullable=False)
    show_genre = db.Column(db.Boolean, default=True, nullable=False)
    profile_image_url = db.Column(db.String(2048), nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
