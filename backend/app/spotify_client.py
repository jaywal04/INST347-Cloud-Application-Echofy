"""Spotify Web API helpers (token must stay on the server)."""

from __future__ import annotations

import os
from typing import Any

import requests

SPOTIFY_API = "https://api.spotify.com/v1"
# Official Spotify chart playlist (Top 50 — Global); public, works with many token types.
GLOBAL_TOP_50_PLAYLIST = "37i9dQZEVXbMDoHDwVN2tF"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token.strip()}"}


def _normalize_track(item: dict[str, Any]) -> dict[str, Any] | None:
    if not item or item.get("is_local"):
        return None
    album = item.get("album") or {}
    images = album.get("images") or []
    image_url = next((img.get("url") for img in images if img.get("url")), None)
    artists = [a.get("name", "") for a in item.get("artists") or [] if a.get("name")]
    return {
        "name": item.get("name") or "Unknown track",
        "artists": artists,
        "album": album.get("name") or "",
        "image": image_url,
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


def fetch_top_tracks_for_response(token: str) -> tuple[dict[str, Any], int]:
    """
    Try the user's top tracks first; if that fails (e.g. client-credentials token),
    fall back to the global Top 50 playlist.
    Returns (json_dict, http_status).
    """
    if not token or not token.strip():
        return (
            {
                "error": "missing_token",
                "message": "Set JAY_SPOTIFY_TOKEN in your .env file (repo root).",
            },
            503,
        )

    headers = _headers(token)
    timeout = 20

    me = requests.get(
        f"{SPOTIFY_API}/me/top/tracks",
        headers=headers,
        params={"limit": 20, "time_range": "short_term"},
        timeout=timeout,
    )
    if me.status_code == 200:
        tracks = []
        for item in me.json().get("items") or []:
            t = _normalize_track(item)
            if t:
                tracks.append(t)
        if tracks:
            return ({"source": "your_top_tracks", "tracks": tracks}, 200)
        # Empty listening history — fall back to chart playlist

    pl = requests.get(
        f"{SPOTIFY_API}/playlists/{GLOBAL_TOP_50_PLAYLIST}/tracks",
        headers=headers,
        params={"limit": 30},
        timeout=timeout,
    )
    if pl.status_code != 200:
        detail = ""
        try:
            detail = pl.json().get("error", {}).get("message", "") or pl.text[:300]
        except Exception:
            detail = pl.text[:300]
        return (
            {
                "error": "spotify_api_error",
                "status": pl.status_code,
                "message": "Spotify rejected the request. Token may be expired or lack required scopes.",
                "detail": detail,
            },
            502,
        )

    tracks = []
    for row in pl.json().get("items") or []:
        t = _normalize_track(row.get("track") or {})
        if t:
            tracks.append(t)

    return ({"source": "global_top_50", "tracks": tracks}, 200)
