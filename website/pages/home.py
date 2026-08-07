import streamlit as st
import pandas as pd

from website.components import (
    page_header,
    metric_row,
)

from website.utils import load_community_price_history, load_dashboard


st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"]::before {
        content: "";
        display: block;
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

comparison, market_summary, effect_summary, item_summary, metadata = load_dashboard()

summary = market_summary

snapshot_time = pd.to_datetime(
    metadata["snapshot_timestamp"]
)

last_updated = snapshot_time.strftime("%d %b %Y")

page_header(
    "Team Fortress 2 Market Intelligence",
    "Analytics platform for the TF2 unusual economy powered by data collected from backpack.tf.",
)

# --------------------------------------------------------------------
# Snapshot Metrics
# --------------------------------------------------------------------

st.subheader("Latest Unusual Market Snapshot")

metric_row([
    ("Markets", f"{summary['total_unusuals']:,}", None),
    ("Effects", effect_summary["effect_name"].nunique(), None),
    ("Items", item_summary["item_name"].nunique(), None),
    ("Last Updated", last_updated, None),
])

st.subheader("Latest Community Price Guide Snapshot")

community_history = load_community_price_history()
required_community_columns = {
    "snapshot_timestamp",
    "priced_variants",
    "unique_items",
    "median_price_keys",
}

if community_history.empty:
    st.info("No cleaned community price-guide snapshot is available yet.")
elif not required_community_columns.issubset(community_history.columns):
    st.warning(
        "The community price-guide snapshot uses an older format. Re-run the "
        "community cleaner to update it."
    )
else:
    latest_community = community_history.iloc[-1]
    community_updated = latest_community["snapshot_timestamp"].strftime("%d %b %Y")
    metric_row([
        ("Price Guide Entries", f"{int(latest_community['priced_variants']):,}", None),
        ("Different Items", f"{int(latest_community['unique_items']):,}", None),
        ("Median Item Value", f"{latest_community['median_price_keys']:.2f} keys", None),
        ("Last Updated", community_updated, None),
    ])

st.divider()

# --------------------------------------------------------------------
# Welcome
# --------------------------------------------------------------------

st.header("Welcome to TFAnalytics")

st.write(
    """
TFAnalytics is an analytics platform built for the **Team Fortress 2
unusual economy**.

Using market data collected from **backpack.tf**, TFAnalytics transforms
thousands of market listings into interactive dashboards, summaries,
historical comparisons and downloadable reports.

Whether you're a trader, collector or simply interested in the TF2
economy, the platform helps you understand market movements at a glance.
"""
)

st.divider()

# --------------------------------------------------------------------
# Features
# --------------------------------------------------------------------

st.header("Explore the Platform")

col1, col2 = st.columns(2)

with col1:

    st.info(
        """
### Market Overview

View the latest market snapshot.

- Price increases
- Price decreases
- New listings
- Market activity
"""
    )

    if st.button(
    "Open Dashboard",
    use_container_width=True,
):
        st.switch_page("website/pages/dashboard.py")

    st.info(
        """
### Item Guide

Analyse TF2 items.

- Item leaderboards
- Largest movers
- Market statistics
"""
    )

    if st.button(
    "Open Items",
    use_container_width=True,
):
        st.switch_page("website/pages/items.py")

with col2:

    st.info(
        """
### Effect Guide

Compare unusual effects.

- Effect leaderboards
- Biggest gainers
- Biggest losers
- Average price changes
"""
    )

    if st.button(
    "Open Effects",
    use_container_width=True,
):
        st.switch_page("website/pages/effects.py")

    st.info(
        """
### Downloads

Download generated datasets.

- Comparison reports
- CSV exports
- Processed market data
"""
    )

    if st.button(
    "Open Reports",
    use_container_width=True,
):
        st.switch_page("website/pages/reports.py")

st.divider()

st.caption(
    "TFAnalytics | Built with Python, Selenium and Streamlit | "
    "Market data sourced from backpack.tf"
)
