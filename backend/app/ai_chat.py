"""Azure OpenAI chat endpoint (deployed via Azure AI Foundry)."""

from __future__ import annotations

import logging
import os

from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import func, desc

from .database import db
from .models import ReviewLike, SongReview, User

logger = logging.getLogger(__name__)

ai_chat_bp = Blueprint("ai_chat", __name__)


def _foundry_configured() -> bool:
    return bool(
        os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "").strip()
        and os.environ.get("AZURE_AI_FOUNDRY_KEY", "").strip()
    )


def _get_client():
    endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "").strip()
    key = os.environ.get("AZURE_AI_FOUNDRY_KEY", "").strip()
    api_version = os.environ.get("AZURE_AI_API_VERSION", "2024-12-01-preview").strip()
    if not endpoint or not key:
        return None
    try:
        from openai import AzureOpenAI

        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=api_version,
        )
    except Exception as exc:
        logger.warning("Failed to create Azure OpenAI client: %s", exc)
        return None


def _build_review_context() -> str:
    """Return the top 25 community reviews as a plain-text block for the system prompt."""
    try:
        like_sq = (
            db.session.query(
                ReviewLike.song_review_id,
                func.count(ReviewLike.id).label("like_count"),
            )
            .group_by(ReviewLike.song_review_id)
            .subquery()
        )
        rows = (
            db.session.query(
                SongReview,
                User.username,
                func.coalesce(like_sq.c.like_count, 0),
            )
            .join(User, User.id == SongReview.user_id)
            .outerjoin(like_sq, like_sq.c.song_review_id == SongReview.id)
            .order_by(
                desc(func.coalesce(like_sq.c.like_count, 0)),
                desc(SongReview.rating),
            )
            .limit(25)
            .all()
        )
    except Exception as exc:
        logger.warning("Could not load reviews for AI context: %s", exc)
        return "No review data available."

    if not rows:
        return "No reviews have been posted yet."

    lines = []
    for review, username, likes in rows:
        stars = "★" * review.rating + "☆" * (5 - review.rating)
        artists = review.artists or ""
        by = f" by {artists}" if artists else ""
        line = f'- {username} rated "{review.name}"{by} ({review.item_type}) {stars} ({likes} likes)'
        if review.text:
            snippet = review.text[:120].replace("\n", " ")
            line += f' — "{snippet}"'
        lines.append(line)
    return "\n".join(lines)


_SYSTEM_TEMPLATE = """\
You are Echo AI, the assistant for Echofy — a music review and discovery platform.
Users rate and review tracks, albums, and artists and connect with friends.

Here are the current top community reviews (ordered by likes then star rating):
{context}

Use this data to help users:
- Discover what music is popular on the platform
- Get personalized suggestions based on community tastes
- Understand what genres, artists, or albums are trending
- Summarize what the community thinks about specific music

Be concise, enthusiastic about music, and ground your answers in the review data when relevant.\
"""


@ai_chat_bp.get("/api/chat/status")
def chat_status():
    return jsonify({"ok": True, "configured": _foundry_configured()})


@ai_chat_bp.post("/api/chat")
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"ok": False, "error": "message required"}), 400
    if len(message) > 1000:
        return jsonify({"ok": False, "error": "Message too long (max 1000 chars)"}), 400

    client = _get_client()
    if not client:
        return jsonify({"ok": False, "error": "AI chat is not configured on this server"}), 503

    deployment = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o")
    context = _build_review_context()

    messages = [{"role": "system", "content": _SYSTEM_TEMPLATE.format(context=context)}]
    for turn in history[-10:]:
        role = (turn.get("role") or "").lower()
        content = (turn.get("content") or "")[:2000]
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        return jsonify({"ok": True, "reply": reply})
    except Exception as exc:
        logger.error("Azure OpenAI error: %s", exc)
        return jsonify({"ok": False, "error": "AI service error. Please try again."}), 502
