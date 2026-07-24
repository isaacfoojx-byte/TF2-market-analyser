import streamlit as st
import pandas as pd

from website.components import (
    page_header,
    metric_row,
)

from website.utils import load_dashboard

st.set_page_config(
    page_title="TFAnalytics",
    page_icon="🎩",
    layout="wide",
    initial_sidebar_state="expanded",
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

comparison, market_summary, effect_summary, item_summary, metadata = load_dashboard()

summary = market_summary.iloc[0]

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

st.subheader("Latest Market Snapshot")

metric_row([
    ("🎩 Markets", f"{summary['total_unusuals']:,}", None),
    ("✨ Effects", effect_summary["effect_name"].nunique(), None),
    ("📦 Items", item_summary["item_name"].nunique(), None),
    ("🕒 Last Updated", last_updated, None),
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
### 📈 Market Overview

View the latest market snapshot.

- Price increases
- Price decreases
- New listings
- Market activity
"""
    )

    st.info(
        """
### 📦 Item Analytics

Analyse TF2 items.

- Item leaderboards
- Largest movers
- Market statistics
"""
    )

with col2:

    st.info(
        """
### ✨ Effect Analytics

Compare unusual effects.

- Effect leaderboards
- Biggest gainers
- Biggest losers
- Average price changes
"""
    )

    st.info(
        """
### 📄 Reports

Download generated datasets.

- Comparison reports
- CSV exports
- Processed market data
"""
    )

st.divider()

st.caption(
    "TFAnalytics • Built with Python, Selenium and Streamlit • "
    "Market data sourced from backpack.tf"
)