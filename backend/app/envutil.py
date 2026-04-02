"""Environment lookups: try keys in order; first non-empty wins (supports SPOTIFY_* and legacy JAY_*)."""

from __future__ import annotations

import os


def first_non_empty(*keys: str, default: str = "") -> str:
    """Return the first stripped non-empty value for the given keys, else default."""
    for key in keys:
        raw = os.environ.get(key)
        if raw is None:
            continue
        s = raw.strip()
        if s:
            return s
    return default
