import streamlit as st

from analytics.snapshot_comparison import (
    build_comparison,
    calculate_changes,
    classify_changes,
    build_market_summary,
)

st.set_page_config(
    page_title="Market Overview",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Market Overview")

comparison = build_comparison()
comparison = calculate_changes(comparison)
comparison = classify_changes(comparison)

market_summary = build_market_summary(comparison)

st.subheader("Market Overview")

st.dataframe(market_summary)