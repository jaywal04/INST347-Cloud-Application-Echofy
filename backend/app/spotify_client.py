"""Spotify Web API helpers (credentials must stay on the server)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import requests

from app.envutil import first_non_empty

SPOTIFY_API = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
# Official Spotify chart playlist (Top 50 — Global); public, works with client credentials.
GLOBAL_TOP_50_PLAYLIST = "37i9dQZEVXbMDoHDwVN2tF"

_REFRESH_MARGIN_SEC = 60
_REQUEST_TIMEOUT = 20
# Spotify GET /v1/search: limit must be 0–10 (inclusive). Values above 10 return "Invalid limit".
_SPOTIFY_SEARCH_MAX_LIMIT = 10
_SEARCH_LIMIT = 10
_GENRE_RESULT_LIMIT = 12
_GENRE_RECOMMENDATION_LIMIT = 50
_GENRE_ARTIST_SEARCH_LIMIT = 10
_GENRE_TRACKS_PER_ARTIST = 8
_GENRE_SEEDS = (
    "afrobeat",
    "alternative",
    "anime",
    "blues",
    "chill",
    "classical",
    "country",
    "dancehall",
    "drill",
    "edm",
    "electronic",
    "emo",
    "folk",
    "funk",
    "gospel",
    "grime",
    "hip-hop",
    "house",
    "indie",
    "jazz",
    "k-pop",
    "latin",
    "lo-fi",
    "metal",
    "phonk",
    "pop",
    "punk",
    "r-n-b",
    "rap",
    "reggaeton",
    "rock",
    "shoegaze",
    "soul",
    "techno",
    "trap",
)
_POPULAR_GENRE_ARTISTS = {
    "rap": ["Drake", "Kendrick Lamar", "J. Cole", "Future", "Lil Baby", "21 Savage", "Travis Scott", "Tyler, The Creator", "Gunna", "Young Thug"],
    "hip-hop": ["Drake", "Kendrick Lamar", "Travis Scott", "Tyler, The Creator", "J. Cole", "Future", "A$AP Rocky", "Lil Baby", "Doja Cat", "21 Savage"],
    "trap": ["Future", "Young Thug", "Lil Baby", "Gunna", "21 Savage", "Travis Scott", "Lil Uzi Vert", "Playboi Carti", "Kodak Black", "Chief Keef"],
    "pop": ["Taylor Swift", "Dua Lipa", "The Weeknd", "Ariana Grande", "Olivia Rodrigo", "Sabrina Carpenter", "Harry Styles", "Ed Sheeran", "Justin Bieber", "Billie Eilish"],
    "rock": ["Foo Fighters", "Arctic Monkeys", "Red Hot Chili Peppers", "The Killers", "Green Day", "Paramore", "The Strokes", "Linkin Park", "Kings of Leon", "Coldplay"],
    "country": ["Morgan Wallen", "Luke Combs", "Zach Bryan", "Chris Stapleton", "Lainey Wilson", "Kane Brown", "Bailey Zimmerman", "Jason Aldean", "Luke Bryan", "Thomas Rhett"],
    "house": ["Fred again..", "FISHER", "John Summit", "Chris Lake", "MK", "Dom Dolla", "Mau P", "Disclosure", "Jamie xx", "Vintage Culture"],
    "afrobeat": ["Burna Boy", "Wizkid", "Rema", "Asake", "Tems", "Davido", "Ayra Starr", "Fireboy DML", "Omah Lay", "CKay"],
    "r-n-b": ["SZA", "Summer Walker", "Brent Faiyaz", "PARTYNEXTDOOR", "H.E.R.", "Giveon", "Jhene Aiko", "6LACK", "The Weeknd", "Usher"],
    "reggaeton": ["Bad Bunny", "Feid", "J Balvin", "Karol G", "Rauw Alejandro", "Ozuna", "Anuel AA", "Myke Towers", "Daddy Yankee", "Nicky Jam"],
    "latin": ["Bad Bunny", "Peso Pluma", "Karol G", "Rauw Alejandro", "J Balvin", "Feid", "Shakira", "Anitta", "Manuel Turizo", "Myke Towers"],
    "indie": ["Phoebe Bridgers", "The 1975", "beabadoobee", "Clairo", "Mitski", "Wallows", "Japanese Breakfast", "The Neighbourhood", "Men I Trust", "Tame Impala"],
    "electronic": ["Fred again..", "Skrillex", "Disclosure", "Kaytranada", "Jamie xx", "Flume", "ODESZA", "Four Tet", "Bicep", "Channel Tres"],
    "edm": ["Martin Garrix", "Avicii", "Calvin Harris", "Zedd", "David Guetta", "Kygo", "Alesso", "Swedish House Mafia", "Marshmello", "Tiësto"],
    "techno": ["Charlotte de Witte", "Amelie Lens", "Adam Beyer", "Boris Brejcha", "Carl Cox", "Nina Kraviz", "ARTBAT", "Tale Of Us", "Enrico Sangiuliano", "Anyma"],
    "drill": ["Pop Smoke", "Lil Durk", "Central Cee", "Headie One", "Fivio Foreign", "Sheff G", "Sleepy Hallow", "Polo G", "Digga D", "King Von"],
    "k-pop": ["BTS", "BLACKPINK", "NewJeans", "Stray Kids", "TWICE", "SEVENTEEN", "aespa", "LE SSERAFIM", "TXT", "IVE"],
}
_GENRE_ALIASES = {
    "rap": ["rap", "hip hop", "hip-hop", "trap", "drill"],
    "hip-hop": ["hip hop", "hip-hop", "rap", "alternative hip hop", "underground hip hop"],
    "trap": ["trap"],
    "pop": ["pop", "dance pop", "electropop", "bedroom pop"],
    "rock": ["rock", "alternative rock", "indie rock", "hard rock", "modern rock", "punk"],
    "country": ["country", "country road", "contemporary country", "outlaw country"],
    "house": ["house", "deep house", "tech house", "progressive house"],
    "afrobeat": ["afrobeat", "afrobeats", "nigerian pop"],
    "r-n-b": ["r&b", "r-n-b", "rnb", "soul", "neo soul"],
    "reggaeton": ["reggaeton"],
    "latin": ["latin", "latin pop", "latin trap", "urbano latino"],
    "indie": ["indie", "indie pop", "indie rock", "indietronica"],
    "electronic": ["electronic", "electronica", "downtempo"],
    "edm": ["edm", "dance", "big room", "festival"],
    "techno": ["techno"],
    "drill": ["drill", "brooklyn drill", "uk drill"],
    "k-pop": ["k-pop", "k pop"],
    "jazz": ["jazz"],
    "soul": ["soul"],
    "metal": ["metal", "metalcore", "deathcore", "heavy metal"],
    "folk": ["folk", "folk-pop"],
    "phonk": ["phonk"],
}

_cc_lock = threading.Lock()
_cc_access_token: str | None = None
_cc_expires_at_monotonic: float = 0.0
_cc_client_key: tuple[str, str] | None = None


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token.strip()}"}


def _normalize_catalog_track(item: dict[str, Any]) -> dict[str, Any] | None:
    """Map a Spotify track object to Echofy item shape (non-local, catalog)."""
    if not item:
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


def _normalize_track(item: dict[str, Any]) -> dict[str, Any] | None:
    if not item or item.get("is_local"):
        return None
    return _normalize_catalog_track(item)


def _normalize_playlist_track_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """
    Normalize a `track` object from GET /playlists/{id}/items rows (may be track, episode,
    local file, or null if removed).
    """
    if not item:
        return None
    if item.get("type") == "episode":
        show = item.get("show") or {}
        images = item.get("images") or []
        image_url = next((img.get("url") for img in images if img.get("url")), None)
        pub = (show.get("publisher") or "").strip()
        show_name = (show.get("name") or "Podcast").strip()
        artists = [pub] if pub else [show_name]
        return {
            "type": "episode",
            "name": item.get("name") or "Episode",
            "artists": artists,
            "album": f"{show_name} · Episode",
            "image": image_url,
            "url": (item.get("external_urls") or {}).get("spotify"),
        }
    if item.get("is_local"):
        album = item.get("album") or {}
        images = album.get("images") or []
        image_url = next((img.get("url") for img in images if img.get("url")), None)
        artists = [a.get("name", "") for a in item.get("artists") or [] if a.get("name")]
        return {
            "type": "track",
            "name": item.get("name") or "Local file",
            "artists": artists if artists else ["Local"],
            "album": (album.get("name") or "").strip() or "This device",
            "image": image_url,
            "url": (item.get("external_urls") or {}).get("spotify"),
            "is_local": True,
        }
    return _normalize_catalog_track(item)


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


def _pretty_genre_name(genre: str) -> str:
    return " ".join(part.capitalize() for part in (genre or "").replace("-", " ").split())


def _normalize_genre_item(genre: str) -> dict[str, Any]:
    seed = (genre or "").strip().lower()
    return {
        "type": "genre",
        "name": _pretty_genre_name(seed) or "Genre",
        "artists": [],
        "album": "Genre seed",
        "image": None,
        "url": "",
        "genre_seed": seed,
    }


def _normalize_search_item(item: dict[str, Any], item_type: str) -> dict[str, Any] | None:
    if item_type == "track":
        return _normalize_track(item)
    if item_type == "album":
        return _normalize_album(item)
    if item_type == "artist":
        return _normalize_artist(item)
    return None


def _canonical_genre(values: list[str] | tuple[str, ...] | None) -> str | None:
    haystacks = [str(value or "").strip().lower() for value in (values or []) if str(value or "").strip()]
    if not haystacks:
        return None
    for canonical, aliases in _GENRE_ALIASES.items():
        for haystack in haystacks:
            if canonical in haystack:
                return canonical
            if any(alias in haystack for alias in aliases):
                return canonical
    return None


def _artist_search_items(access_token: str, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
    res = requests.get(
        f"{SPOTIFY_API}/search",
        headers=_headers(access_token),
        params={"q": query, "type": "artist", "limit": limit},
        timeout=_REQUEST_TIMEOUT,
    )
    if res.status_code != 200:
        return []
    return (res.json().get("artists") or {}).get("items") or []


def _infer_genre_from_item(access_token: str, item: dict[str, Any]) -> str | None:
    item_type = str(item.get("type") or "").strip().lower()
    if item_type == "genre":
        return _canonical_genre([item.get("genre_seed") or item.get("name") or ""])

    if item_type == "artist":
        metadata = str(item.get("album") or "")
        genre = _canonical_genre([metadata, item.get("name") or ""])
        if genre:
            return genre
        artists = _artist_search_items(access_token, str(item.get("name") or ""), limit=1)
        if artists:
            return _canonical_genre((artists[0].get("genres") or []) + [artists[0].get("name") or ""])
        return None

    artists = item.get("artists") or []
    lead_artist = str(artists[0] if artists else "").strip()
    if not lead_artist:
        return None
    artist_hits = _artist_search_items(access_token, lead_artist, limit=1)
    if not artist_hits:
        return None
    return _canonical_genre((artist_hits[0].get("genres") or []) + [lead_artist])


def _resolve_spotify_token(
    client_id: str = "",
    client_secret: str = "",
    legacy_user_token: str = "",
    oauth_access_token: str = "",
) -> tuple[str | None, str | None, tuple[dict[str, Any], int] | None]:
    token = (oauth_access_token or legacy_user_token or "").strip()
    if token:
        return token, "user", None

    cid, csec = client_id.strip(), client_secret.strip()
    if cid and csec:
        token, err = _get_client_credentials_token(cid, csec)
        if token:
            return token, "client", None
        return None, None, (
            {
                "error": "token_error",
                "message": err or "Could not obtain Spotify access token.",
            },
            502,
        )

    return None, None, (
        {
            "error": "missing_credentials",
            "message": "Connect Spotify or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET on the backend.",
        },
        503,
    )


def _playlist_tracks_payload(
    access_token: str, playlist_id: str, *, market: str | None
) -> tuple[list[dict[str, Any]] | None, str]:
    """Returns (tracks_list, error_detail). tracks_list None if request failed or empty."""
    m = (market or "").strip().upper()
    if len(m) != 2 or not m.isalpha():
        m = _spotify_iso_market()
    params: dict[str, Any] = {
        "limit": 30,
        "additional_types": "episode,track",
        "market": m,
    }
    pl = requests.get(
        f"{SPOTIFY_API}/playlists/{playlist_id}/items",
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
        t = _normalize_playlist_track_item(row.get("track") or {})
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


def refresh_spotify_user_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> tuple[str | None, str | None, str]:
    """
    Exchange a refresh token for a new access token.
    Returns (access_token, new_refresh_token_or_none, error_message).
    error_message is empty on success.
    """
    rt = (refresh_token or "").strip()
    cid, csec = (client_id or "").strip(), (client_secret or "").strip()
    if not rt or not cid or not csec:
        return None, None, "missing_refresh_credentials"

    r = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": rt},
        auth=(cid, csec),
        timeout=_REQUEST_TIMEOUT,
    )
    if r.status_code != 200:
        try:
            detail = r.json().get("error_description") or r.json().get("error", "")
        except Exception:
            detail = ""
        return None, None, detail or r.text[:300] or f"HTTP {r.status_code}"

    data = r.json()
    access = data.get("access_token")
    if not access or not isinstance(access, str):
        return None, None, "refresh response missing access_token"

    new_refresh = data.get("refresh_token")
    if isinstance(new_refresh, str) and new_refresh.strip():
        return access.strip(), new_refresh.strip(), ""

    return access.strip(), None, ""


def _spotify_iso_market() -> str:
    """Spotify expects a 2-letter ISO market; bad values (e.g. 'USA') can break search."""
    m = first_non_empty("SPOTIFY_MARKET", "JAY_SPOTIFY_MARKET", default="US").strip().upper()
    if len(m) == 2 and m.isalpha():
        return m
    return "US"


def _search_tracks_client_fallback(
    access_token: str, market: str
) -> tuple[list[dict[str, Any]] | None, str]:
    """When browse/chart endpoints fail, track search usually still works (client credentials)."""
    m = (market or "").strip().upper()
    if len(m) != 2 or not m.isalpha():
        m = "US"

    queries = (
        "genre:pop",
        "genre:hip-hop",
        "genre:rock",
        "year:2024",
        "pop",
        "hip hop",
        "rock",
    )

    def run(with_market: bool) -> tuple[list[dict[str, Any]] | None, str]:
        last_local = ""
        for q in queries:
            params: dict[str, Any] = {
                "q": q,
                "type": "track",
                "limit": _SPOTIFY_SEARCH_MAX_LIMIT,
            }
            if with_market:
                params["market"] = m
            res = requests.get(
                f"{SPOTIFY_API}/search",
                headers=_headers(access_token),
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            if res.status_code != 200:
                try:
                    body = res.json()
                    err = body.get("error") or {}
                    last_local = (
                        str(err.get("message", "") or err.get("reason", "") or "").strip()
                        or res.text[:160]
                        or f"HTTP {res.status_code}"
                    ).strip()
                except Exception:
                    last_local = (res.text[:160] or f"HTTP {res.status_code}").strip()
                continue
            tracks: list[dict[str, Any]] = []
            for raw in (res.json().get("tracks") or {}).get("items") or []:
                t = _normalize_track(raw)
                if t:
                    tracks.append(t)
            if tracks:
                return tracks, ""
        return None, last_local

    tracks, err = run(True)
    if tracks:
        return tracks, ""
    tracks, err2 = run(False)
    if tracks:
        return tracks, ""
    tail = (err2 or err or "track search returned no usable results").strip()
    return None, tail


def fetch_public_chart(access_token: str) -> tuple[dict[str, Any], int]:
    """
    Chart-style content for Client Credentials (and user-token fallback).
    Global Top 50 often returns 403 for app-only tokens; we fall back to new releases
    and featured playlists (all allowed for client credentials).
    """
    last_detail = ""

    market = _spotify_iso_market()

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

    st_tracks, st_err = _search_tracks_client_fallback(access_token, market)
    if st_tracks:
        return ({"source": "search_explore", "tracks": st_tracks}, 200)
    if st_err:
        last_detail = st_err

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
        err_status = me.status_code if me.status_code in (401, 403) else 502
        return (
            {
                "error": "invalid_user_token",
                "message": "Spotify user token is missing, expired, or lacks user-top-read. Use Connect Spotify or set Client ID + Secret for the chart.",
                "status": me.status_code,
            },
            err_status,
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
    oauth_refresh_token: str = "",
    on_token_refresh: Callable[[str, str | None], None] | None = None,
) -> tuple[dict[str, Any], int]:
    """
    Prefer a connected Spotify user token for personalized top tracks.
    Refreshes the access token when Spotify returns 401/403 and a refresh token is available.
    Falls back to Client Credentials for a public chart when no user token is available,
    or when the user token cannot load /me/top/tracks even after refresh.
    """
    user = (oauth_access_token or legacy_user_token or "").strip()
    cid, csec = client_id.strip(), client_secret.strip()
    refresh_tok = (oauth_refresh_token or "").strip()
    used_oauth = bool((oauth_access_token or "").strip())

    if user:
        payload, status = _legacy_user_then_playlist(user)
        if status in (401, 403) and refresh_tok and cid and csec and on_token_refresh and used_oauth:
            new_access, new_refresh, err = refresh_spotify_user_access_token(
                cid, csec, refresh_tok
            )
            if new_access:
                on_token_refresh(new_access, new_refresh)
                payload, status = _legacy_user_then_playlist(new_access)
        if status in (401, 403) and cid and csec:
            token, err = _get_client_credentials_token(cid, csec)
            if token:
                chart_payload, chart_status = fetch_public_chart(token)
                if chart_status == 200:
                    chart_payload["spotify_session_note"] = (
                        "Personalized top tracks were unavailable (expired login or missing "
                        "user-top-read). Showing a public Spotify chart instead — use "
                        "Connect Spotify again for your own top tracks."
                    )
                    return chart_payload, chart_status
        return payload, status

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
    if kind not in {"track", "album", "artist", "genre"}:
        return (
            {
                "error": "invalid_type",
                "message": "Search type must be track, album, artist, or genre.",
            },
            400,
        )

    token, _token_source, token_error = _resolve_spotify_token(
        client_id=client_id,
        client_secret=client_secret,
        legacy_user_token=legacy_user_token,
        oauth_access_token=oauth_access_token,
    )
    if token_error:
        return token_error
    if not token:
        return (
            {
                "error": "missing_credentials",
                "message": "Connect Spotify or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET on the backend.",
            },
            503,
        )

    if kind == "genre":
        needle = q.lower()
        items = [_normalize_genre_item(seed) for seed in _GENRE_SEEDS if needle in seed.lower()][: _GENRE_RESULT_LIMIT]
        return (
            {
                "source": "spotify_genre_search",
                "query": q,
                "type": kind,
                "items": items,
            },
            200,
        )

    params: dict[str, Any] = {"q": q, "type": kind, "limit": _SEARCH_LIMIT}
    market = _spotify_iso_market()
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


def _get_playlist_items_first_page(
    playlist_id: str, access_token: str, page_limit: int
) -> requests.Response:
    """GET /v1/playlists/{id}/items (current API; /tracks is legacy)."""
    return requests.get(
        f"{SPOTIFY_API}/playlists/{playlist_id}/items",
        headers=_headers(access_token),
        params={
            "limit": min(100, max(1, page_limit)),
            "additional_types": "episode,track",
            "market": _spotify_iso_market(),
        },
        timeout=_REQUEST_TIMEOUT,
    )


def fetch_playlist_tracks_for_response(
    oauth_access_token: str = "",
    playlist_id: str = "",
    limit: int = 500,
    oauth_refresh_token: str = "",
    client_id: str = "",
    client_secret: str = "",
    on_token_refresh: Callable[[str, str | None], None] | None = None,
) -> tuple[dict[str, Any], int]:
    """Fetch up to `limit` playlist items (tracks/episodes) via GET /playlists/{id}/items."""
    token = (oauth_access_token or "").strip()
    pid = (playlist_id or "").strip()
    if not token:
        return ({"error": "no_user_token", "message": "Connect your Spotify account first."}, 401)
    if not pid:
        return ({"error": "missing_playlist_id", "message": "Playlist ID is required."}, 400)

    cap = min(max(1, limit), 1000)
    refresh_tok = (oauth_refresh_token or "").strip()
    cid, csec = client_id.strip(), client_secret.strip()
    used_oauth = bool((oauth_access_token or "").strip())

    active_token = token
    res = _get_playlist_items_first_page(pid, active_token, min(100, cap))

    if res.status_code in (401, 403) and refresh_tok and cid and csec and on_token_refresh and used_oauth:
        new_access, new_refresh, _err = refresh_spotify_user_access_token(
            cid, csec, refresh_tok
        )
        if new_access:
            on_token_refresh(new_access, new_refresh)
            active_token = new_access
            res = _get_playlist_items_first_page(pid, active_token, min(100, cap))

    if res.status_code == 401:
        return ({"error": "token_expired", "message": "Spotify session expired. Reconnect your account."}, 401)
    if res.status_code == 403:
        detail = ""
        try:
            err = res.json().get("error") or {}
            detail = (err.get("message") or "").strip()
        except Exception:
            detail = (res.text or "")[:200]
        low = detail.lower()
        if "scope" in low:
            return (
                {
                    "error": "insufficient_scope",
                    "message": "Missing Spotify permission. Disconnect and reconnect Spotify to approve all requested scopes.",
                    "detail": detail,
                },
                403,
            )
        generic = not detail or detail.lower() == "forbidden"
        return (
            {
                "error": "spotify_forbidden",
                "message": (
                    "Spotify blocked this playlist’s tracks. You must own the playlist or be a "
                    "collaborator (Spotify no longer exposes full track lists for playlists you only "
                    "follow). If it is yours, disconnect and reconnect Spotify so the token includes "
                    "user-read-private (account country) and playlist scopes."
                    if generic
                    else detail
                ),
                "detail": detail,
            },
            403,
        )
    if res.status_code == 404:
        return ({"error": "not_found", "message": "Playlist not found or is private."}, 404)
    if res.status_code != 200:
        try:
            detail = res.json().get("error", {}).get("message", "") or res.text[:200]
        except Exception:
            detail = res.text[:200]
        return ({"error": "spotify_api_error", "message": "Could not load playlist tracks.", "detail": detail}, 502)

    body = res.json()
    total = body.get("total", 0)
    raw_items: list[dict[str, Any]] = list(body.get("items") or [])
    next_url = (body.get("next") or "").strip() or None
    while next_url and len(raw_items) < cap:
        page = requests.get(
            next_url,
            headers=_headers(active_token),
            timeout=_REQUEST_TIMEOUT,
        )
        if page.status_code != 200:
            break
        chunk = page.json()
        raw_items.extend(chunk.get("items") or [])
        next_url = (chunk.get("next") or "").strip() or None

    tracks = []
    for row in raw_items[:cap]:
        wrapped = row.get("track")
        if wrapped is None and isinstance(row.get("item"), dict):
            wrapped = row["item"]
        t = _normalize_playlist_track_item(wrapped or {})
        if t:
            tracks.append(t)

    return ({"tracks": tracks, "total": total, "returned": len(tracks)}, 200)


def fetch_user_playlists_for_response(
    oauth_access_token: str = "",
    limit: int = 50,
    oauth_refresh_token: str = "",
    client_id: str = "",
    client_secret: str = "",
    on_token_refresh: Callable[[str, str | None], None] | None = None,
) -> tuple[dict[str, Any], int]:
    """
    Fetch the current user's playlists via /v1/me/playlists.
    Requires a user OAuth token with playlist-read-private scope.
    """
    token = (oauth_access_token or "").strip()
    if not token:
        return (
            {
                "error": "no_user_token",
                "message": "Connect your Spotify account to view your playlists.",
            },
            401,
        )

    refresh_tok = (oauth_refresh_token or "").strip()
    cid, csec = client_id.strip(), client_secret.strip()
    used_oauth = bool((oauth_access_token or "").strip())

    res = requests.get(
        f"{SPOTIFY_API}/me/playlists",
        headers=_headers(token),
        params={"limit": min(limit, 50)},
        timeout=_REQUEST_TIMEOUT,
    )

    if res.status_code in (401, 403) and refresh_tok and cid and csec and on_token_refresh and used_oauth:
        new_access, new_refresh, _err = refresh_spotify_user_access_token(
            cid, csec, refresh_tok
        )
        if new_access:
            on_token_refresh(new_access, new_refresh)
            token = new_access
            res = requests.get(
                f"{SPOTIFY_API}/me/playlists",
                headers=_headers(token),
                params={"limit": min(limit, 50)},
                timeout=_REQUEST_TIMEOUT,
            )

    if res.status_code == 401:
        return (
            {
                "error": "token_expired",
                "message": "Spotify session expired. Disconnect and reconnect your Spotify account.",
            },
            401,
        )

    if res.status_code == 403:
        return (
            {
                "error": "insufficient_scope",
                "message": "Missing playlist-read-private permission. Disconnect and reconnect Spotify to grant access.",
            },
            403,
        )

    if res.status_code != 200:
        try:
            detail = res.json().get("error", {}).get("message", "") or res.text[:200]
        except Exception:
            detail = res.text[:200]
        return (
            {
                "error": "spotify_api_error",
                "message": "Could not load playlists from Spotify.",
                "detail": detail,
            },
            502,
        )

    playlists = []
    for p in res.json().get("items") or []:
        if not p:
            continue
        images = p.get("images") or []
        image_url = next((img.get("url") for img in images if img.get("url")), None)
        tr_ref = p.get("tracks") or {}
        tc = tr_ref.get("total")
        playlists.append({
            "id": p.get("id") or "",
            "name": p.get("name") or "Untitled Playlist",
            "description": p.get("description") or "",
            "image": image_url,
            "track_count": tc if tc is not None else None,
            "owner": (p.get("owner") or {}).get("display_name") or "",
            "url": (p.get("external_urls") or {}).get("spotify") or "",
            "public": p.get("public", False),
            "collaborative": p.get("collaborative", False),
        })

    return ({"playlists": playlists, "total": len(playlists)}, 200)


def recommend_tracks_for_genre_response(
    client_id: str = "",
    client_secret: str = "",
    legacy_user_token: str = "",
    oauth_access_token: str = "",
    genre: str = "",
) -> tuple[dict[str, Any], int]:
    seed = (genre or "").strip().lower()
    if len(seed) < 2:
        return (
            {
                "error": "invalid_genre",
                "message": "Pick a genre before asking for a recommendation.",
            },
            400,
        )

    token, _token_source, token_error = _resolve_spotify_token(
        client_id=client_id,
        client_secret=client_secret,
        legacy_user_token=legacy_user_token,
        oauth_access_token=oauth_access_token,
    )
    if token_error:
        return token_error
    if not token:
        return (
            {
                "error": "missing_credentials",
                "message": "Connect Spotify or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET on the backend.",
            },
            503,
        )

    market = _spotify_iso_market()
    headers = _headers(token)

    artist_names = list(_POPULAR_GENRE_ARTISTS.get(seed, []))

    artist_search = requests.get(
        f"{SPOTIFY_API}/search",
        headers=headers,
        params={"q": f"genre:{seed}", "type": "artist", "limit": _GENRE_ARTIST_SEARCH_LIMIT},
        timeout=_REQUEST_TIMEOUT,
    )
    if artist_search.status_code == 200:
        for artist in (artist_search.json().get("artists") or {}).get("items") or []:
            name = str(artist.get("name") or "").strip()
            if name and name.lower() not in [existing.lower() for existing in artist_names]:
                artist_names.append(name)

    items = []
    seen_urls = set()

    for artist_name in artist_names:
        for offset in (0, _GENRE_TRACKS_PER_ARTIST):
            params = {
                "q": f'artist:"{artist_name}"',
                "type": "track",
                "limit": _GENRE_TRACKS_PER_ARTIST,
                "offset": offset,
            }
            if market:
                params["market"] = market
            res = requests.get(
                f"{SPOTIFY_API}/search",
                headers=headers,
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            if res.status_code != 200:
                continue
            for raw in (res.json().get("tracks") or {}).get("items") or []:
                artist_names_on_track = [str(a.get("name") or "").strip().lower() for a in raw.get("artists") or []]
                if artist_name.lower() not in artist_names_on_track:
                    continue
                item = _normalize_track(raw)
                if not item:
                    continue
                dedupe_key = item.get("url") or f"{item.get('name','')}|{','.join(item.get('artists') or [])}"
                if dedupe_key in seen_urls:
                    continue
                seen_urls.add(dedupe_key)
                items.append(item)
                if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
                    break
            if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
                break
        if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
            break

    for offset in (0, 10, 20, 30, 40):
        if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
            break
        params = {
            "q": f"genre:{seed}",
            "type": "track",
            "limit": 10,
            "offset": offset,
        }
        if market:
            params["market"] = market
        res = requests.get(
            f"{SPOTIFY_API}/search",
            headers=headers,
            params=params,
            timeout=_REQUEST_TIMEOUT,
        )
        if res.status_code != 200:
            if not items:
                try:
                    detail = res.json().get("error", {}).get("message", "") or res.text[:200]
                except Exception:
                    detail = res.text[:200]
                return (
                    {
                        "error": "spotify_recommendation_error",
                        "message": "Could not load Spotify recommendations for that genre.",
                        "detail": detail,
                    },
                    502,
                )
            continue
        for raw in (res.json().get("tracks") or {}).get("items") or []:
            item = _normalize_track(raw)
            if not item:
                continue
            dedupe_key = item.get("url") or f"{item.get('name','')}|{','.join(item.get('artists') or [])}"
            if dedupe_key in seen_urls:
                continue
            seen_urls.add(dedupe_key)
            items.append(item)
            if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
                break

    return (
        {
            "source": "spotify_genre_recommendations",
            "genre": seed,
            "tracks": items,
        },
        200,
    )


def recommend_similar_for_item_response(
    client_id: str = "",
    client_secret: str = "",
    legacy_user_token: str = "",
    oauth_access_token: str = "",
    item: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    seed_item = item or {}
    item_type = str(seed_item.get("type") or "track").strip().lower()
    if item_type not in {"track", "album", "artist"}:
        return (
            {
                "error": "invalid_item_type",
                "message": "Recommendations are supported for tracks, albums, and artists.",
            },
            400,
        )

    token, _token_source, token_error = _resolve_spotify_token(
        client_id=client_id,
        client_secret=client_secret,
        legacy_user_token=legacy_user_token,
        oauth_access_token=oauth_access_token,
    )
    if token_error:
        return token_error
    if not token:
        return (
            {
                "error": "missing_credentials",
                "message": "Connect Spotify or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET on the backend.",
            },
            503,
        )

    genre = _infer_genre_from_item(token, seed_item)
    if not genre:
        return (
            {
                "error": "genre_inference_failed",
                "message": "Could not determine a genre for that Spotify item.",
            },
            422,
        )

    market = _spotify_iso_market()
    headers = _headers(token)
    artist_names = list(_POPULAR_GENRE_ARTISTS.get(genre, []))
    for artist in _artist_search_items(token, f"genre:{genre}", limit=_GENRE_ARTIST_SEARCH_LIMIT):
        name = str(artist.get("name") or "").strip()
        if name and name.lower() not in [existing.lower() for existing in artist_names]:
            artist_names.append(name)

    items = []
    seen = set()
    seed_name = str(seed_item.get("name") or "").strip().lower()
    seed_url = str(seed_item.get("url") or "").strip()

    for artist_name in artist_names:
        for offset in (0, _GENRE_TRACKS_PER_ARTIST):
            params = {
                "q": f'artist:"{artist_name}"',
                "type": item_type,
                "limit": _GENRE_TRACKS_PER_ARTIST,
                "offset": offset,
            }
            if market and item_type in {"track", "album"}:
                params["market"] = market
            res = requests.get(
                f"{SPOTIFY_API}/search",
                headers=headers,
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            if res.status_code != 200:
                continue
            bucket = (res.json().get(f"{item_type}s") or {}).get("items") or []
            for raw in bucket:
                normalized = _normalize_search_item(raw, item_type)
                if not normalized:
                    continue
                dedupe_key = normalized.get("url") or f"{normalized.get('name','')}|{','.join(normalized.get('artists') or [])}|{normalized.get('album') or ''}"
                if dedupe_key in seen:
                    continue
                if seed_url and normalized.get("url") == seed_url:
                    continue
                if seed_name and str(normalized.get("name") or "").strip().lower() == seed_name:
                    continue
                seen.add(dedupe_key)
                items.append(normalized)
                if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
                    break
            if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
                break
        if len(items) >= _GENRE_RECOMMENDATION_LIMIT:
            break

    return (
        {
            "source": "spotify_similar_recommendations",
            "genre": genre,
            "seed_type": item_type,
            "seed_name": seed_item.get("name") or "",
            "items": items,
        },
        200,
    )
