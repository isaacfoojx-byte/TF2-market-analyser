import streamlit as st
import pandas as pd

from website.components import (
    page_header,
    metric_row,
)

from website.utils import (
    load_community_price_history,
    load_latest_unusual_snapshot,
)


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

latest_snapshot = load_latest_unusual_snapshot()

if latest_snapshot is None:
    st.error("No processed Unusual market snapshot is available.")
    st.stop()

snapshot_time = pd.to_datetime(latest_snapshot["snapshot_timestamp"])

last_updated = snapshot_time.strftime("%d %b %Y")

page_header(
    "Team Fortress 2 Market Intelligence",
    "Market intelligence for the wider Team Fortress 2 economy, using Unusual market data and backpack.tf community price-guide data.",
)

# --------------------------------------------------------------------
# Snapshot Metrics
# --------------------------------------------------------------------

st.subheader("Latest Unusual Market Snapshot")

metric_row([
    (
        "Unique Unusual Markets",
        f"{latest_snapshot['priced_markets']:,}",
        None,
        "Each exact Unusual market: one effect paired with one item. The same hat "
        "with different effects counts as separate markets.",
    ),
    ("Distinct Effects", latest_snapshot["unique_effects"], None),
    (
        "Distinct Hats",
        latest_snapshot["unique_items"],
        None,
        "Unique hat and item names regardless of their Unusual effect. A hat counts "
        "once even when it appears with many effects.",
    ),
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
        (
            "Price Guide Entries",
            f"{int(latest_community['priced_variants']):,}",
            None,
            "Each separately priced version of an item. Quality and craftability "
            "make separate entries—for example, Unique and Strange versions of the "
            "same item count separately.",
        ),
        (
            "Different Items",
            f"{int(latest_community['unique_items']):,}",
            None,
            "Unique base item names only. An item such as Team Captain counts once "
            "even when it has several quality or craftability variants.",
        ),
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
TFAnalytics is an analytics platform built for the **wider Team Fortress 2
market**.

Using Unusual market data and community price-guide data collected from
**backpack.tf**, TFAnalytics transforms thousands of item values into
interactive dashboards, summaries, historical comparisons and downloadable datasets.

Whether you're a trader, collector or simply interested in the TF2 economy,
the platform helps you understand Unusual and non-Unusual item values at a glance.
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
