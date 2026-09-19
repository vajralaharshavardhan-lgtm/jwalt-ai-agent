"""Shared helpers for agents that must never invent missing data."""
from __future__ import annotations

UNKNOWN = "UNKNOWN"


def present(value) -> bool:
    return value not in (None, "", [], {})


def or_unknown(value):
    return value if present(value) else UNKNOWN
