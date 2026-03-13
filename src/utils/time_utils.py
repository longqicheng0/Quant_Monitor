"""Time helper functions used across modules."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def to_iso(ts: datetime) -> str:
    """Format datetime as ISO string."""
    return ts.isoformat()
