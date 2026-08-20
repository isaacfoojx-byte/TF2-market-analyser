import streamlit as st

from analytics.community_history import (
    community_history_signature,
    load_community_catalog,
    load_community_history,
    load_community_item_trend,
)
from analytics.history import (
    history_signature,
    load_latest_market_snapshot,
    load_market_history,
    load_unusual_catalog,
    load_unusual_trend,
)

from analytics.snapshot_comparison import (
    build_comparison,
    calculate_changes,
    classify_changes,
    build_market_summary,
    build_effect_summary,
    build_item_summary,
)

from analytics.metadata import load_metadata


@st.cache_data
def _load_market(signature: tuple[tuple[str, int, int], ...]):
    comparison = build_comparison()
    comparison = calculate_changes(comparison)
    comparison = classify_changes(comparison)

    return comparison


@st.cache_data
def _load_dashboard(signature: tuple[tuple[str, int, int], ...]):
    comparison = _load_market(signature)
    metadata = dict(load_metadata() or {})
    latest_snapshot = load_latest_market_snapshot()

    # generated/metadata.json is an optional scrape artifact and may not be
    # committed with the CSVs. The displayed date must follow the actual data.
    if latest_snapshot is not None:
        metadata["snapshot_timestamp"] = latest_snapshot[
            "snapshot_timestamp"
        ].isoformat()

    return (
        comparison,
        build_market_summary(comparison),
        build_effect_summary(comparison),
        build_item_summary(comparison),
        metadata,
    )


def load_market():
    """Load the newest comparison, refreshing when processed CSVs change."""

    return _load_market(history_signature())


def load_dashboard():
    """Load dashboard data, refreshing when processed CSVs change."""

    return _load_dashboard(history_signature())


@st.cache_data
def _load_effects(signature: tuple[tuple[str, int, int], ...]):
    comparison = _load_market(signature)

    return (
        comparison,
        build_effect_summary(comparison),
    )


@st.cache_data
def _load_items(signature: tuple[tuple[str, int, int], ...]):
    comparison = _load_market(signature)

    return (
        comparison,
        build_item_summary(comparison),
    )


def load_effects():
    """Load effect summaries, refreshing when processed CSVs change."""

    return _load_effects(history_signature())


def load_items():
    """Load item summaries, refreshing when processed CSVs change."""

    return _load_items(history_signature())


@st.cache_data
def _load_history(signature: tuple[tuple[str, int, int], ...]):
    """Load aggregate history from every processed market snapshot."""

    return load_market_history()


def load_history():
    """Load history and refresh the cache whenever processed snapshots change."""

    return _load_history(history_signature())


@st.cache_data
def _load_unusual_catalog(signature: tuple[tuple[str, int, int], ...]):
    return load_unusual_catalog()


def load_unusual_markets():
    """Load item/effect selectors from the latest snapshot."""

    return _load_unusual_catalog(history_signature())


@st.cache_data
def _load_latest_unusual_snapshot(
    signature: tuple[tuple[str, int, int], ...],
):
    return load_latest_market_snapshot()


def load_latest_unusual_snapshot():
    """Load headline metrics from the newest processed unusual CSV."""

    return _load_latest_unusual_snapshot(history_signature())


@st.cache_data
def _load_unusual_trend(
    effect_id: int,
    defindex: int,
    signature: tuple[tuple[str, int, int], ...],
):
    return load_unusual_trend(effect_id, defindex)


def load_unusual_market_trend(effect_id: int, defindex: int):
    """Load the trend for one exact unusual market across all snapshots."""

    return _load_unusual_trend(effect_id, defindex, history_signature())


@st.cache_data
def _load_community_history(signature: tuple[tuple[str, int, int], ...]):
    return load_community_history()


def load_community_price_history():
    """Load guide-price history and refresh the cache after a cleaned scrape."""

    return _load_community_history(community_history_signature())


@st.cache_data
def _load_community_catalog(signature: tuple[tuple[str, int, int], ...]):
    return load_community_catalog()


def load_community_markets():
    """Load latest item/quality/craftability selectors from guide snapshots."""

    return _load_community_catalog(community_history_signature())


@st.cache_data
def _load_community_item_trend(
    item_name: str,
    quality: str,
    craftable: bool | None,
    signature: tuple[tuple[str, int, int], ...],
):
    return load_community_item_trend(item_name, quality, craftable)


def load_community_market_trend(
    item_name: str,
    quality: str,
    craftable: bool | None,
):
    """Load guide-price history for one exact non-Unusual item variant."""

    return _load_community_item_trend(
        item_name,
        quality,
        craftable,
        community_history_signature(),
    )
