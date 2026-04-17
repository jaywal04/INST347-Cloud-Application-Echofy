"""Spotify Web API helpers (credentials must stay on the server)."""

from __future__ import annotations

import threading
import time
from typing import Any

import requests

from app.envutil import first_non_empty

SPOTIFY_API = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
# Official Spotify chart playlist (Top 50 — Global); public, works with client credentials.
GLOBAL_TOP_50_PLAYLIST = "37i9dQZEVXbMDoHDwVN2tF"

_REFRESH_MARGIN_SEC = 60
_REQUEST_TIMEOUT = 20

_cc_lock = threading.Lock()
_cc_access_token: str | None = None
_cc_expires_at_monotonic: float = 0.0
_cc_client_key: tuple[str, str] | None = None


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token.strip()}"}


def _normalize_track(item: dict[str, Any]) -> dict[str, Any] | None:
    if not item or item.get("is_local"):
        return None
    album = item.get("album") or {}
    images = album.get("images") or []
    image_url = next((img.get("url") for img in images if img.get("url")), None)
    artists = [a.get("name", "") for a in item.get("artists") or [] if a.get("name")]
    return {
        "type": "track",
        "name": item.get("name") or "Unknown track",
        "artists": artists,
        "album": album.get("name") or "",
        "image": image_url,
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


def _normalize_new_release_album(album: dict[str, Any]) -> dict[str, Any] | None:
    if not album:
        return None
    images = album.get("images") or []
    image_url = next((img.get("url") for img in images if img.get("url")), None)
    artists = [a.get("name", "") for a in album.get("artists") or [] if a.get("name")]
    return {
        "type": "album",
        "name": album.get("name") or "Album",
        "artists": artists,
        "album": "New release",
        "image": image_url,
        "url": (album.get("external_urls") or {}).get("spotify"),
    }


def _normalize_album(item: dict[str, Any]) -> dict[str, Any] | None:
    if not item:
        return None
    images = item.get("images") or []
    image_url = next((img.get("url") for img in images if img.get("url")), None)
    artists = [a.get("name", "") for a in item.get("artists") or [] if a.get("name")]
    release_year = (item.get("release_date") or "")[:4]
    album_type = (item.get("album_type") or "album").title()
    if release_year:
        album_type = f"{album_type} · {release_year}"
    return {
        "type": "album",
        "name": item.get("name") or "Album",
        "artists": artists,
        "album": album_type,
        "image": image_url,
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


def _normalize_artist(item: dict[str, Any]) -> dict[str, Any] | None:
    if not item:
        return None
    images = item.get("images") or []
    image_url = next((img.get("url") for img in images if img.get("url")), None)
    genres = item.get("genres") or []
    followers = (item.get("followers") or {}).get("total")
    detail = ", ".join(genres[:2]) if genres else "Artist"
    if followers:
        detail = f"{detail} · {followers:,} followers"
    return {
        "type": "artist",
        "name": item.get("name") or "Artist",
        "artists": [],
        "album": detail,
        "image": image_url,
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


def _normalize_search_item(item: dict[str, Any], item_type: str) -> dict[str, Any] | None:
    if item_type == "track":
        return _normalize_track(item)
    if item_type == "album":
        return _normalize_album(item)
    if item_type == "artist":
        return _normalize_artist(item)
    return None


def _playlist_tracks_payload(
    access_token: str, playlist_id: str, *, market: str | None
) -> tuple[list[dict[str, Any]] | None, str]:
    """Returns (tracks_list, error_detail). tracks_list None if request failed or empty."""
    params: dict[str, Any] = {"limit": 30}
    if market:
        params["market"] = market
    pl = requests.get(
        f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
        headers=_headers(access_token),
        params=params,
        timeout=_REQUEST_TIMEOUT,
    )
    if pl.status_code != 200:
        try:
            detail = pl.json().get("error", {}).get("message", "") or pl.text[:200]
        except Exception:
            detail = pl.text[:200]
        return None, detail or f"HTTP {pl.status_code}"

    tracks = []
    for row in pl.json().get("items") or []:
        t = _normalize_track(row.get("track") or {})
        if t:
            tracks.append(t)
    return (tracks if tracks else None), ""


def _get_client_credentials_token(client_id: str, client_secret: str) -> tuple[str | None, str]:
    """
    Return (access_token, error_message). error_message is empty on success.
    Uses an in-memory cache until shortly before Spotify's expires_in.
    """
    global _cc_access_token, _cc_expires_at_monotonic, _cc_client_key

    cid, csec = client_id.strip(), client_secret.strip()
    now = time.monotonic()
    key = (cid, csec)

    with _cc_lock:
        if (
            _cc_access_token
            and now < _cc_expires_at_monotonic
            and _cc_client_key == key
        ):
            return _cc_access_token, ""

        r = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(cid, csec),
            timeout=_REQUEST_TIMEOUT,
        )

        if r.status_code != 200:
            try:
                err = r.json().get("error_description") or r.json().get("error", "")
            except Exception:
                err = ""
            detail = err or r.text[:300]
            return None, f"Spotify token request failed ({r.status_code}): {detail}"

        data = r.json()
        token = data.get("access_token")
        if not token:
            return None, "Spotify token response missing access_token"

        expires_in = int(data.get("expires_in", 3600))
        _cc_access_token = token
        _cc_expires_at_monotonic = now + max(30, expires_in - _REFRESH_MARGIN_SEC)
        _cc_client_key = key

        return token, ""


def fetch_public_chart(access_token: str) -> tuple[dict[str, Any], int]:
    """
    Chart-style content for Client Credentials (and user-token fallback).
    Global Top 50 often returns 403 for app-only tokens; we fall back to new releases
    and featured playlists (all allowed for client credentials).
    """
    last_detail = ""

    market = first_non_empty("SPOTIFY_MARKET", "JAY_SPOTIFY_MARKET", default="US")

    market_attempts: list[str | None] = []
    if market:
        market_attempts.append(market)
    market_attempts.append(None)

    for m in market_attempts:
        tracks, err = _playlist_tracks_payload(
            access_token, GLOBAL_TOP_50_PLAYLIST, market=m
        )
        if tracks:
            return ({"source": "global_top_50", "tracks": tracks}, 200)
        if err:
            last_detail = err

    nr = requests.get(
        f"{SPOTIFY_API}/browse/new-releases",
        headers=_headers(access_token),
        params={"limit": 20},
        timeout=_REQUEST_TIMEOUT,
    )
    if nr.status_code == 200:
        tracks = []
        for album in nr.json().get("albums", {}).get("items") or []:
            row = _normalize_new_release_album(album)
            if row:
                tracks.append(row)
        if tracks:
            return ({"source": "new_releases", "tracks": tracks}, 200)
    else:
        try:
            last_detail = nr.json().get("error", {}).get("message", "") or nr.text[:200]
        except Exception:
            last_detail = nr.text[:200]

    feat = requests.get(
        f"{SPOTIFY_API}/browse/featured-playlists",
        headers=_headers(access_token),
        params={"limit": 15},
        timeout=_REQUEST_TIMEOUT,
    )
    if feat.status_code == 200:
        for p in feat.json().get("playlists", {}).get("items") or []:
            pid = p.get("id")
            pname = p.get("name") or "Featured"
            if not pid:
                continue
            tracks, err = _playlist_tracks_payload(access_token, pid, market=None)
            if tracks:
                return (
                    {
                        "source": "featured_playlist",
                        "tracks": tracks,
                        "playlist_name": pname,
                    },
                    200,
                )
            if err:
                last_detail = err
    else:
        try:
            last_detail = feat.json().get("error", {}).get("message", "") or feat.text[:200]
        except Exception:
            last_detail = feat.text[:200]

    msg = "Could not load music from Spotify."
    if last_detail:
        msg = f"{msg} Last error: {last_detail}"
    return (
        {
            "error": "spotify_api_error",
            "message": msg,
            "detail": last_detail,
        },
        502,
    )


def _legacy_user_then_playlist(user_token: str) -> tuple[dict[str, Any], int]:
    """Try /me/top/tracks, then Global Top 50 using the same user token (only if /me succeeds)."""
    headers = _headers(user_token)

    me = requests.get(
        f"{SPOTIFY_API}/me/top/tracks",
        headers=headers,
        params={"limit": 20, "time_range": "short_term"},
        timeout=_REQUEST_TIMEOUT,
    )
    if me.status_code not in (200,):
        # Do not call the Web API with an invalid/expired user token (would yield 502).
        return (
            {
                "error": "invalid_user_token",
                "message": "Spotify user token is missing, expired, or lacks user-top-read. Use Connect Spotify or set Client ID + Secret for the chart.",
                "status": me.status_code,
            },
            401,
        )

    tracks = []
    for item in me.json().get("items") or []:
        t = _normalize_track(item)
        if t:
            tracks.append(t)
    if tracks:
        return ({"source": "your_top_tracks", "tracks": tracks}, 200)

    return fetch_public_chart(user_token.strip())


def fetch_top_tracks_for_response(
    client_id: str = "",
    client_secret: str = "",
    legacy_user_token: str = "",
    oauth_access_token: str = "",
) -> tuple[dict[str, Any], int]:
    """
    When Client ID + Secret are set: load Global Top 50 via Client Credentials (dashboard chart).
    Otherwise: OAuth / legacy user token for personalized top tracks + playlist fallback.
    """
    user = (oauth_access_token or legacy_user_token or "").strip()
    cid, csec = client_id.strip(), client_secret.strip()

    if cid and csec:
        token, err = _get_client_credentials_token(cid, csec)
        if not token:
            return (
                {
                    "error": "token_error",
                    "message": err or "Could not obtain Spotify access token.",
                },
                502,
            )
        return fetch_public_chart(token)

    if user:
        return _legacy_user_then_playlist(user)

    return (
        {
            "error": "missing_credentials",
            "message": (
                "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env "
                "(repo root) for the chart, or connect Spotify / set SPOTIFY_TOKEN. "
                "Legacy JAY_SPOTIFY_* names still work if SPOTIFY_* are empty."
            ),
        },
        503,
    )


def search_spotify_for_response(
    client_id: str = "",
    client_secret: str = "",
    legacy_user_token: str = "",
    oauth_access_token: str = "",
    query: str = "",
    item_type: str = "track",
) -> tuple[dict[str, Any], int]:
    q = (query or "").strip()
    kind = (item_type or "track").strip().lower()
    if len(q) < 2:
        return (
            {
                "error": "invalid_query",
                "message": "Search for at least 2 characters.",
            },
            400,
        )
    if kind not in {"track", "album", "artist"}:
        return (
            {
                "error": "invalid_type",
                "message": "Search type must be track, album, or artist.",
            },
            400,
        )

    cid, csec = client_id.strip(), client_secret.strip()
    token = (oauth_access_token or legacy_user_token or "").strip()
    if cid and csec:
        token, err = _get_client_credentials_token(cid, csec)
        if not token:
            return (
                {
                    "error": "token_error",
                    "message": err or "Could not obtain Spotify access token.",
                },
                502,
            )
    elif not token:
        return (
            {
                "error": "missing_credentials",
                "message": "Connect Spotify or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET on the backend.",
            },
            503,
        )

    params: dict[str, Any] = {"q": q, "type": kind, "limit": 20}
    market = first_non_empty("SPOTIFY_MARKET", "JAY_SPOTIFY_MARKET", default="US")
    if kind in {"track", "album"} and market:
        params["market"] = market

    res = requests.get(
        f"{SPOTIFY_API}/search",
        headers=_headers(token),
        params=params,
        timeout=_REQUEST_TIMEOUT,
    )
    if res.status_code != 200:
        try:
            detail = res.json().get("error", {}).get("message", "") or res.text[:200]
        except Exception:
            detail = res.text[:200]
        return (
            {
                "error": "spotify_search_error",
                "message": "Could not search Spotify.",
                "detail": detail,
            },
            502,
        )

    bucket = res.json().get(f"{kind}s") or {}
    items = []
    for raw in bucket.get("items") or []:
        item = _normalize_search_item(raw, kind)
        if item:
            items.append(item)

    return (
        {
            "source": "spotify_search",
            "query": q,
            "type": kind,
            "items": items,
        },
        200,
    )
