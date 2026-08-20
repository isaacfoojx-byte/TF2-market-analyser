"""Site-wide checks for missing or stale market snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from analytics.community_history import get_community_snapshots
from analytics.utils import get_snapshots


MAX_SNAPSHOT_AGE = timedelta(hours=36)


def _timestamp_from_filename(path: Path, prefix: str) -> datetime | None:
    timestamp = path.stem.removeprefix(prefix)
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        return None


def freshness_messages(
    now: datetime | None = None,
    unusual_snapshots: list[Path] | None = None,
    community_snapshots: list[Path] | None = None,
    maximum_age: timedelta = MAX_SNAPSHOT_AGE,
) -> list[str]:
    """Describe any missing or stale datasets for a user-facing warning."""

    current_time = now or datetime.now(timezone.utc).replace(tzinfo=None)
    sources = (
        (
            "Unusual market",
            unusual_snapshots if unusual_snapshots is not None else get_snapshots(),
            "cleaned_",
        ),
        (
            "Community price-guide",
            community_snapshots
            if community_snapshots is not None
            else get_community_snapshots(),
            "community_prices_",
        ),
    )

    messages: list[str] = []
    for label, snapshots, prefix in sources:
        if not snapshots:
            messages.append(f"{label} data is unavailable.")
            continue

        latest = _timestamp_from_filename(snapshots[-1], prefix)
        if latest is None:
            messages.append(f"{label} data has an unreadable update timestamp.")
            continue

        age = current_time - latest
        if age > maximum_age:
            messages.append(
                f"{label} data may be stale; its last snapshot was "
                f"{latest.strftime('%d %b %Y at %H:%M')} UTC."
            )

    return messages


def data_freshness_notice() -> None:
    """Render one warning when either production dataset needs attention."""

    messages = freshness_messages()
    if messages:
        st.warning(" ".join(messages), icon="⚠️")
