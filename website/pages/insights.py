import pandas as pd
import streamlit as st

from insights import (
    calculate_market_sentiment,
    detect_market_risks,
    find_opportunities,
    generate_effect_insights,
    generate_item_insights,
    generate_market_insights,
)
from website.components import metric_row, page_header, show_table
from website.utils import load_dashboard


def spotlight(summary: pd.DataFrame, name_column: str, minimum_markets: int):
    """Choose a positive mover with enough represented markets to be useful."""

    candidates = spotlight_candidates(summary, name_column, minimum_markets)

    if candidates.empty:
        return None

    return candidates.loc[candidates["average_change"].idxmax()]


def spotlight_candidates(
    summary: pd.DataFrame,
    name_column: str,
    minimum_markets: int,
) -> pd.DataFrame:
    """Return the same thresholded data used by each spotlight card."""

    required = {name_column, "average_change", "unusuals"}
    if summary.empty or not required.issubset(summary.columns):
        return pd.DataFrame()

    candidates = summary.dropna(subset=[name_column, "average_change", "unusuals"])
    candidates = candidates.loc[candidates["unusuals"] >= minimum_markets]

    return candidates


def column_maximum(
    dataframe: pd.DataFrame,
    column: str,
    fallback: int,
) -> int:
    """Return a usable widget maximum even when a column is empty or invalid."""

    if column not in dataframe.columns:
        return fallback

    values = pd.to_numeric(dataframe[column], errors="coerce").dropna()
    if values.empty:
        return fallback

    return max(fallback, int(values.max()))


comparison, market_summary, effect_summary, item_summary, metadata = load_dashboard()

page_header(
    "💡 Market Insights",
    "Explainable market sentiment, risk flags, and opportunity screening from the latest comparison.",
)

if metadata is not None and metadata.get("snapshot_timestamp"):
    st.caption(f"Latest snapshot: {metadata['snapshot_timestamp']}")

sentiment = calculate_market_sentiment(comparison)
risks = detect_market_risks(comparison)

if sentiment["score"] is None:
    metric_row([
        ("Market Sentiment", "Unavailable", None),
        ("Confidence", sentiment["confidence"], None),
    ])
    st.warning(sentiment["reason"])
else:
    metric_row([
        (
            "Market Sentiment",
            f"{sentiment['label']} ({sentiment['score']}/100)",
            None,
        ),
        ("Confidence", sentiment["confidence"], None),
        ("Rising Markets", f"{sentiment['breadth_percent']:.1f}%", None),
        ("Median Movement", f"{sentiment['median_change_keys']:+.2f} keys", None),
    ])
    st.caption(sentiment["reason"])

st.divider()

overview_tab, opportunities_tab, spotlights_tab = st.tabs([
    "Market Overview",
    "Opportunity Detector",
    "Effect & Item Spotlights",
])

with overview_tab:
    st.subheader("Market Narrative")

    for insight in generate_market_insights(comparison, market_summary):
        st.write(f"• {insight}")

    st.subheader("Risk Detector")

    if risks and risks[0].startswith("No broad"):
        st.success(risks[0])
    else:
        for risk in risks:
            st.warning(risk)

with opportunities_tab:
    st.subheader("Opportunity Detector")
    st.caption(
        "Candidates must be rising in price, have stable or falling listing supply, "
        "and meet the selected liquidity threshold. This is a screening tool, not investment advice."
    )

    maximum_listings = column_maximum(comparison, "listings_new", fallback=3)

    if maximum_listings > 3:
        minimum_listings = st.slider(
            "Minimum current listings",
            min_value=3,
            max_value=maximum_listings,
            value=min(5, maximum_listings),
            help="Higher thresholds reduce the chance that a signal comes from a thin market.",
        )
    else:
        minimum_listings = 3
        st.caption(
            "The available comparison has no markets with more than three current listings, "
            "so the liquidity threshold is fixed at three."
        )

    opportunities = find_opportunities(
        comparison,
        minimum_listings=minimum_listings,
    )

    if opportunities.empty:
        st.info(
            "No markets increased in price while meeting the selected liquidity "
            "and listing-supply conditions."
        )
    else:
        opportunity_columns = [
            "effect_name",
            "item_name",
            "percent_change",
            "listing_change",
            "listings_new",
            "opportunity_score",
        ]
        opportunities = opportunities[opportunity_columns].copy()
        opportunities["percent_change"] = opportunities["percent_change"].map(
            "{:+.2f}%".format
        )
        opportunities["listing_change"] = opportunities["listing_change"].map(
            "{:+.0f}".format
        )
        opportunities = opportunities.rename(columns={
            "effect_name": "Effect",
            "item_name": "Item",
            "percent_change": "Price Change",
            "listing_change": "Listing Change",
            "listings_new": "Current Listings",
            "opportunity_score": "Opportunity Score",
        })
        show_table(opportunities)

with spotlights_tab:
    st.subheader("Effect Spotlight")
    maximum_markets = max(
        column_maximum(effect_summary, "unusuals", fallback=1),
        column_maximum(item_summary, "unusuals", fallback=1),
    )

    if maximum_markets > 1:
        minimum_markets = st.slider(
            "Minimum markets represented in a spotlight",
            min_value=1,
            max_value=maximum_markets,
            value=1,
            key="spotlight_minimum_markets",
        )
    else:
        minimum_markets = 1
        st.caption(
            "Only one represented market is available, so the spotlight threshold is fixed at one."
        )

    effect_spotlight = spotlight(
        effect_summary,
        "effect_name",
        minimum_markets,
    )
    item_spotlight = spotlight(
        item_summary,
        "item_name",
        minimum_markets,
    )
    spotlight_effects = spotlight_candidates(
        effect_summary,
        "effect_name",
        minimum_markets,
    )
    spotlight_items = spotlight_candidates(
        item_summary,
        "item_name",
        minimum_markets,
    )

    effect_column, item_column = st.columns(2)

    with effect_column:
        st.markdown("#### ✨ Effect Spotlight")
        if effect_spotlight is None:
            st.info("No effect meets this market threshold.")
        else:
            st.metric(
                effect_spotlight["effect_name"],
                f"{effect_spotlight['average_change']:+.2f} keys",
                f"{int(effect_spotlight['unusuals'])} markets represented",
            )
            for insight in generate_effect_insights(spotlight_effects):
                st.write(f"• {insight}")

    with item_column:
        st.markdown("#### 📦 Item Spotlight")
        if item_spotlight is None:
            st.info("No item meets this market threshold.")
        else:
            st.metric(
                item_spotlight["item_name"],
                f"{item_spotlight['average_change']:+.2f} keys",
                f"{int(item_spotlight['unusuals'])} markets represented",
            )
            for insight in generate_item_insights(spotlight_items):
                st.write(f"• {insight}")
