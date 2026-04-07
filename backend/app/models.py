"""Database models."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db


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
    profile_image_url = db.Column(db.String(2048), nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
