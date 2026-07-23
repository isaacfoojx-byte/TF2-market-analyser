import streamlit as st

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
def load_market_data():
    comparison = build_comparison()
    comparison = calculate_changes(comparison)
    comparison = classify_changes(comparison)

    return comparison


@st.cache_data
def load_dashboard_data():
    comparison = load_market_data()

    return (
        comparison,
        build_market_summary(comparison),
        build_effect_summary(comparison),
        build_item_summary(comparison),
        load_metadata(),
    )


@st.cache_data
def load_effect_data():
    comparison = load_market_data()

    return (
        comparison,
        build_effect_summary(comparison),
    )


@st.cache_data
def load_item_data():
    comparison = load_market_data()

    return (
        comparison,
        build_item_summary(comparison),
    )