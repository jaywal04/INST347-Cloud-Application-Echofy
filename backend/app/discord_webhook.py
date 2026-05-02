"""Post structured messages to a Discord incoming webhook (server-side only)."""

from __future__ import annotations

import json
import re
from typing import Any

import requests

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|apikey|api_key|credential)",
    re.I,
)


def sanitize_for_report(obj: Any, max_depth: int = 6, max_str: int = 400) -> Any:
    """Remove likely secrets and cap size for outbound logging."""
    if max_depth < 0:
        return "[truncated-depth]"
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        s = obj.strip()
        if _SENSITIVE_KEY.search(s) and len(s) > 20:
            return "[redacted-string]"
        return s[:max_str] + ("…" if len(s) > max_str else "")
    if isinstance(obj, list):
        return [sanitize_for_report(x, max_depth - 1, max_str) for x in obj[:30]]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in list(obj.items())[:40]:
            if _SENSITIVE_KEY.search(str(k)):
                continue
            out[str(k)[:80]] = sanitize_for_report(v, max_depth - 1, max_str)
        return out
    return str(obj)[:max_str]


def send_client_bug_embed(webhook_url: str, title: str, payload: dict[str, Any]) -> bool:
    """Send one embed to Discord. Returns True if the request was accepted."""
    u = (webhook_url or "").strip()
    if not u.startswith("https://") or "/api/webhooks/" not in u:
        return False
    if "discord.com" not in u and "discordapp.com" not in u:
        return False
    clean = sanitize_for_report(payload)
    try:
        body = json.dumps(clean, indent=2, default=str)[:3500]
    except Exception:
        body = str(clean)[:3500]
    embed = {
        "title": title[:256],
        "description": f"```json\n{body}\n```"[:4090],
        "color": 0xE74C3C,
    }
    try:
        r = requests.post(
            u,
            json={"username": "Echofy", "embeds": [embed]},
            headers={"Content-Type": "application/json"},
            timeout=6,
        )
        return r.status_code in (200, 204)
    except Exception:
        return False
