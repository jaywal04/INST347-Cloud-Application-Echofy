"""Client-side error reporting to Discord (optional)."""

from __future__ import annotations

import time
from typing import Any

from flask import Blueprint, jsonify, request

from app.discord_webhook import send_client_bug_embed
from app.envutil import first_non_empty

telemetry_bp = Blueprint("telemetry", __name__, url_prefix="/api/telemetry")

# Simple per-IP sliding window (best-effort; resets on process restart).
_report_times: dict[str, list[float]] = {}
_WINDOW_SEC = 60.0
_MAX_PER_WINDOW = 20


def _discord_webhook_url() -> str:
    return first_non_empty("DISCORD_WEBHOOK_URL", "ECHOFY_DISCORD_WEBHOOK_URL")


def _rate_allow(ip: str) -> bool:
    now = time.time()
    lst = _report_times.setdefault(ip, [])
    lst[:] = [t for t in lst if now - t < _WINDOW_SEC]
    if len(lst) >= _MAX_PER_WINDOW:
        return False
    lst.append(now)
    return True


@telemetry_bp.post("/client-error")
def client_error():
    """
    Accept a sanitized client bug payload and forward it to Discord if configured.
    Does not require login (so login-page failures can be reported).
    """
    ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or (
        request.remote_addr or "unknown"
    )
    if not _rate_allow(ip):
        return jsonify(ok=True), 200

    webhook = _discord_webhook_url()
    if not webhook:
        return jsonify(ok=True), 200

    if not request.is_json:
        return jsonify(ok=True), 200

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=True), 200

    cl = request.content_length
    if cl is not None and cl > 24_000:
        return jsonify(ok=True), 200

    payload: dict[str, Any] = {
        "client_ip": ip,
        "reported": data,
    }
    send_client_bug_embed(webhook, "Echofy client error", payload)
    return jsonify(ok=True), 200
