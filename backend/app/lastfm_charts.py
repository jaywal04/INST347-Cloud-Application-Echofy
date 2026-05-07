"""Last.fm chart data for Discover — server-side API key only."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.envutil import first_non_empty
from app.spotify_client import (
    SPOTIFY_API,
    _REQUEST_TIMEOUT,
    _headers,
    _normalize_track,
    _spotify_iso_market,
)

_log = logging.getLogger(__name__)

LASTFM_API = "https://ws.audioscrobbler.com/2.0/"

# ISO 3166-1 alpha-2 → English country name for Last.fm geo.getTopTracks
_ISO2_TO_LASTFM_COUNTRY: dict[str, str] = {
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "DE": "Germany",
    "FR": "France",
    "BR": "Brazil",
    "JP": "Japan",
    "ES": "Spain",
    "IT": "Italy",
    "MX": "Mexico",
    "IN": "India",
    "NL": "Netherlands",
    "SE": "Sweden",
    "IE": "Ireland",
    "NZ": "New Zealand",
    "KR": "South Korea",
    "AR": "Argentina",
    "PL": "Poland",
}


def lastfm_api_key_from_env() -> str:
    return first_non_empty(
        "LAST_FM_API_KEY",
        "last_fm_api_key",
        "LASTFM_API_KEY",
    )


def lastfm_geo_country_name() -> str:
    """Country name for Last.fm geo.getTopTracks (not ISO-2)."""
    explicit = first_non_empty(
        "LAST_FM_GEO_COUNTRY",
        "LASTFM_GEO_COUNTRY",
        "last_fm_geo_country",
    ).strip()
    if explicit:
        return explicit
    market = _spotify_iso_market().strip().upper()
    return _ISO2_TO_LASTFM_COUNTRY.get(market, "United States")


def _lastfm_pick_image(track: dict[str, Any]) -> str | None:
    images = track.get("image") or []
    candidates: list[tuple[int, str]] = []
    for img in images:
        if not isinstance(img, dict):
            continue
        url = (img.get("#text") or img.get("url") or "").strip()
        if not url or url.endswith("300x300.png"):
            continue
        size = str(img.get("size") or "").lower()
        order = {"small": 1, "medium": 2, "large": 3, "extralarge": 4}.get(size, 0)
        candidates.append((order, url))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates else None


def _lastfm_request(params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        res = requests.get(LASTFM_API, params=params, timeout=_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        _log.warning("Last.fm request failed: %s", exc)
        return None, str(exc)[:200]
    try:
        data = res.json()
    except Exception as exc:
        return None, str(exc)[:200]
    if isinstance(data.get("error"), int):
        msg = str(data.get("message") or f"Last.fm error {data.get('error')}")
        _log.warning("Last.fm error=%s msg=%s", data.get("error"), msg[:200])
        return None, msg
    return data, None


def _normalize_lf_track_rows(raw_tracks: Any) -> list[dict[str, Any]]:
    if not raw_tracks:
        return []
    if isinstance(raw_tracks, dict):
        raw_tracks = [raw_tracks]
    if not isinstance(raw_tracks, list):
        return []
    rows: list[dict[str, Any]] = []
    for tr in raw_tracks:
        if not isinstance(tr, dict):
            continue
        name = (tr.get("name") or "").strip()
        artist = tr.get("artist")
        artist_name = ""
        if isinstance(artist, dict):
            artist_name = (artist.get("name") or "").strip()
        elif isinstance(artist, str):
            artist_name = artist.strip()
        if not name or not artist_name:
            continue
        listeners = ""
        try:
            listeners = str(tr.get("listeners") or "").strip()
        except Exception:
            pass
        rows.append({
            "name": name,
            "artist_name": artist_name,
            "listeners": listeners,
            "lf_image": _lastfm_pick_image(tr),
            "lf_track_url": (tr.get("url") or "").strip(),
        })
    return rows


def fetch_lastfm_chart_top_tracks_raw(api_key: str, *, limit: int = 45) -> tuple[list[dict[str, Any]], str | None]:
    key = (api_key or "").strip()
    if not key:
        return [], "Last.fm API key is not configured."
    cap = max(1, min(int(limit), 50))
    data, err = _lastfm_request({
        "method": "chart.getTopTracks",
        "api_key": key,
        "format": "json",
        "limit": cap,
    })
    if err or not data:
        return [], err or "Last.fm returned no data."
    raw = ((data.get("tracks") or {}).get("track"))
    return _normalize_lf_track_rows(raw), None


def fetch_lastfm_geo_top_tracks_raw(
    api_key: str, country: str, *, limit: int = 45
) -> tuple[list[dict[str, Any]], str | None]:
    key = (api_key or "").strip()
    if not key:
        return [], "Last.fm API key is not configured."
    ctry = (country or "").strip() or "United States"
    cap = max(1, min(int(limit), 50))
    data, err = _lastfm_request({
        "method": "geo.getTopTracks",
        "api_key": key,
        "format": "json",
        "country": ctry,
        "limit": cap,
    })
    if err or not data:
        return [], err or "Last.fm returned no data."
    raw = ((data.get("tracks") or {}).get("track"))
    return _normalize_lf_track_rows(raw), None


def fetch_lastfm_top_artists_track_rows(
    api_key: str, *, artist_limit: int = 16, per_artist_tracks: int = 6
) -> tuple[list[dict[str, Any]], str | None]:
    """
    chart.getTopArtists, then artist.getTopTracks for each — one chart row per artist (best effort).
    """
    key = (api_key or "").strip()
    if not key:
        return [], "Last.fm API key is not configured."
    cap = max(1, min(int(artist_limit), 30))
    data, err = _lastfm_request({
        "method": "chart.getTopArtists",
        "api_key": key,
        "format": "json",
        "limit": cap,
    })
    if err or not data:
        return [], err or "Last.fm returned no data."
    raw_artists = ((data.get("artists") or {}).get("artist"))
    if isinstance(raw_artists, dict):
        raw_artists = [raw_artists]
    if not isinstance(raw_artists, list):
        raw_artists = []

    rows: list[dict[str, Any]] = []
    per = max(1, min(int(per_artist_tracks), 10))
    for ar in raw_artists:
        if not isinstance(ar, dict):
            continue
        aname = (ar.get("name") or "").strip()
        if not aname:
            continue
        d2, e2 = _lastfm_request({
            "method": "artist.getTopTracks",
            "api_key": key,
            "artist": aname,
            "format": "json",
            "limit": per,
        })
        if e2 or not d2:
            continue
        raw_tt = ((d2.get("toptracks") or {}).get("track"))
        if isinstance(raw_tt, dict):
            raw_tt = [raw_tt]
        if not isinstance(raw_tt, list) or not raw_tt:
            continue
        normalized = _normalize_lf_track_rows(raw_tt[:3])
        if normalized:
            rows.append(normalized[0])

    if not rows:
        return [], "Last.fm returned no playable rows from top artists."
    return rows, None


def fetch_lastfm_rows_for_variant(
    api_key: str,
    variant: str,
    *,
    geo_country: str | None = None,
    limit: int = 45,
) -> tuple[list[dict[str, Any]], str | None]:
    v = (variant or "tracks").strip().lower().replace("-", "_")
    if v in ("tracks", "top_tracks", "chart_tracks"):
        return fetch_lastfm_chart_top_tracks_raw(api_key, limit=limit)
    if v in ("artists", "top_artists", "artist_chart"):
        return fetch_lastfm_top_artists_track_rows(api_key)
    if v in ("geo", "country", "geo_tracks"):
        ctry = (geo_country or "").strip() or lastfm_geo_country_name()
        return fetch_lastfm_geo_top_tracks_raw(api_key, ctry, limit=limit)
    return [], f"Unknown Last.fm variant: {variant!r}"


def spotify_resolve_chart_row(access_token: str, row: dict[str, Any]) -> dict[str, Any] | None:
    """Pick first catalog track match for a Last.fm title + artist."""
    title = row.get("name") or ""
    artist = row.get("artist_name") or ""
    t = title.strip().replace('"', " ")
    a = artist.strip().replace('"', " ")
    if len(t) < 1 or len(a) < 1:
        return None
    q = f"track:{t} artist:{a}"
    market = (_spotify_iso_market() or "").strip()

    params: dict[str, Any] = {"q": q, "type": "track", "limit": 6}
    if market:
        params["market"] = market

    try:
        res = requests.get(
            f"{SPOTIFY_API}/search",
            headers=_headers(access_token),
            params=params,
            timeout=_REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return None
    if res.status_code != 200:
        return None
    items = (res.json().get("tracks") or {}).get("items") or []
    for raw in items:
        nt = _normalize_track(raw or {})
        if nt:
            return nt
    return None


def _source_and_note_for_variant(variant: str, geo_country: str | None) -> tuple[str, str]:
    v = (variant or "tracks").strip().lower().replace("-", "_")
    if v in ("artists", "top_artists", "artist_chart"):
        return (
            "lastfm_top_artists",
            "Last.fm top artists (each entry is that artist’s top track on Last.fm), matched to Spotify.",
        )
    if v in ("geo", "country", "geo_tracks"):
        c = (geo_country or "").strip() or lastfm_geo_country_name()
        return (
            "lastfm_geo_tracks",
            f"Last.fm top tracks in {c}, matched to Spotify.",
        )
    return (
        "lastfm_top_tracks",
        "Last.fm overall top tracks, matched row-by-row to Spotify so tracks can be reviewed here.",
    )


def fetch_lastfm_chart_resolved(
    api_key: str,
    spotify_access_token: str,
    *,
    lastfm_variant: str = "tracks",
    geo_country: str | None = None,
    raw_limit: int = 45,
    max_resolved: int = 28,
) -> tuple[dict[str, Any], int]:
    """
    Load a Last.fm chart variant, then match each row to Spotify via search.

    ``lastfm_variant``: tracks | artists | geo (aliases: top_tracks, top_artists, …)
    """
    v = (lastfm_variant or "tracks").strip().lower().replace("-", "_")
    g = (geo_country or "").strip() or None
    if v in ("geo", "country", "geo_tracks"):
        g = g or lastfm_geo_country_name()

    rows, err = fetch_lastfm_rows_for_variant(api_key, v, geo_country=g, limit=raw_limit)
    if err:
        return (
            {
                "error": "lastfm_chart_error",
                "message": "Could not load Last.fm charts.",
                "detail": err,
            },
            503,
        )
    if not rows:
        return (
            {
                "error": "lastfm_chart_empty",
                "message": "Last.fm returned no chart rows for this source.",
            },
            502,
        )

    token = (spotify_access_token or "").strip()
    if not token:
        return (
            {
                "error": "missing_spotify_token",
                "message": (
                    "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env so the server "
                    "can match Last.fm chart rows to Spotify tracks for reviews."
                ),
            },
            503,
        )

    resolved: list[dict[str, Any]] = []
    cap = max(1, min(int(max_resolved), 35))
    for row in rows:
        if len(resolved) >= cap:
            break
        nt = spotify_resolve_chart_row(token, row)
        if nt:
            resolved.append(nt)

    if not resolved:
        return (
            {
                "error": "lastfm_resolve_failed",
                "message": (
                    "Last.fm charts loaded but no tracks matched Spotify’s catalog "
                    "(check SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET / market)."
                ),
            },
            502,
        )

    source_key, note = _source_and_note_for_variant(v, g)
    return (
        {
            "source": source_key,
            "tracks": resolved,
            "spotify_session_note": note,
            "lastfm_chart_variant": v,
        },
        200,
    )
