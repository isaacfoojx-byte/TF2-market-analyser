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

summary = market_summary.iloc[0]

st.subheader("Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "🎩 Markets",
    f"{summary['total_unusuals']:,}"
)

col2.metric(
    "🆕 New Listings",
    int(summary["new_listings"])
)

col3.metric(
    "📈 Price Increases",
    int(summary["price_up"])
)

col4.metric(
    "📉 Price Decreases",
    int(summary["price_down"])
)

st.divider()

col1, col2, col3 = st.columns(3)

col1.metric(
    "Average Change",
    f"{summary['average_change']:.2f}%"
)

col2.metric(
    "Median Change",
    f"{summary['median_change']:.2f}%"
)

col3.metric(
    "Unchanged",
    int(summary["unchanged"])
)

st.divider()

st.subheader("🔥 Top Movers")

# In order to run this website, type this command in VSCode: python -m streamlit run website/app.py