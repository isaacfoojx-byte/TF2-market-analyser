import streamlit as st

from analytics.community_history import (
    community_history_signature,
    load_community_catalog,
    load_community_history,
    load_community_item_trend,
)
from analytics.history import (
    history_signature,
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
def load_market():
    comparison = build_comparison()
    comparison = calculate_changes(comparison)
    comparison = classify_changes(comparison)

    return comparison


@st.cache_data
def load_dashboard():
    comparison = load_market()

    return (
        comparison,
        build_market_summary(comparison),
        build_effect_summary(comparison),
        build_item_summary(comparison),
        load_metadata(),
    )


@st.cache_data
def load_effects():
    comparison = load_market()

    return (
        comparison,
        build_effect_summary(comparison),
    )


@st.cache_data
def load_items():
    comparison = load_market()

    return (
        comparison,
        build_item_summary(comparison),
    )


@st.cache_data
def _load_history(_: tuple[tuple[str, int, int], ...]):
    """Load aggregate history from every processed market snapshot."""

    return load_market_history()


def load_history():
    """Load history and refresh the cache whenever processed snapshots change."""

    return _load_history(history_signature())


@st.cache_data
def _load_unusual_catalog(_: tuple[tuple[str, int, int], ...]):
    return load_unusual_catalog()


def load_unusual_markets():
    """Load item/effect selectors from the latest snapshot."""

    return _load_unusual_catalog(history_signature())


@st.cache_data
def _load_unusual_trend(
    effect_id: int,
    defindex: int,
    _: tuple[tuple[str, int, int], ...],
):
    return load_unusual_trend(effect_id, defindex)


def load_unusual_market_trend(effect_id: int, defindex: int):
    """Load the trend for one exact unusual market across all snapshots."""

    return _load_unusual_trend(effect_id, defindex, history_signature())


@st.cache_data
def _load_community_history(_: tuple[tuple[str, int, int], ...]):
    return load_community_history()


def load_community_price_history():
    """Load guide-price history and refresh the cache after a cleaned scrape."""

    return _load_community_history(community_history_signature())


@st.cache_data
def _load_community_catalog(_: tuple[tuple[str, int, int], ...]):
    return load_community_catalog()


def load_community_markets():
    """Load latest item/quality/craftability selectors from guide snapshots."""

    return _load_community_catalog(community_history_signature())


@st.cache_data
def _load_community_item_trend(
    item_name: str,
    quality: str,
    craftable: bool | None,
    _: tuple[tuple[str, int, int], ...],
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
