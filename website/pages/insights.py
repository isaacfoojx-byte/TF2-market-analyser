from difflib import get_close_matches
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.history import compare_snapshots
from insights import (
    calculate_market_sentiment,
    detect_market_risks,
    find_opportunities,
    generate_effect_insights,
    generate_item_insights,
    generate_market_insights,
)
from insights.common import assess_spotlight
from website.components import metric_row, page_header, show_table
from website.utils import (
    load_dashboard,
    load_history,
    load_unusual_market_trend,
    load_unusual_markets,
)


def apply_insights_styles() -> None:
    """Apply lightweight, theme-safe polish to the Insights page."""

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1450px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        [data-testid="stMetric"] {
            background: rgba(127, 127, 127, 0.08);
            border: 1px solid rgba(127, 127, 127, 0.22);
            border-radius: 0.75rem;
            padding: 0.9rem 1rem;
        }

        [data-testid="stMetricLabel"] {
            font-weight: 650;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.4rem;
        }

        [data-testid="stTabs"] [data-baseweb="tab"] {
            height: 2.7rem;
            padding: 0 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_snapshot_timestamp(timestamp: str) -> str:
    """Turn an ISO timestamp into a compact, readable UI label."""

    parsed_timestamp = pd.to_datetime(timestamp, errors="coerce")
    if pd.isna(parsed_timestamp):
        return timestamp

    return parsed_timestamp.strftime("%d %b %Y, %H:%M")


def normalise_search_text(value: str) -> str:
    """Make item searches tolerant of case, spacing, and punctuation differences."""

    return re.sub(r"[^a-z0-9]", "", value.lower())


def suggest_items(search_text: str, item_names: list[str]) -> list[str]:
    """Return exact, partial, and close item-name matches without auto-selecting."""

    query = normalise_search_text(search_text)
    if len(query) < 2:
        return []

    normalised_names: dict[str, list[str]] = {}
    word_index: dict[str, list[str]] = {}
    for item_name in item_names:
        normalised_names.setdefault(normalise_search_text(item_name), []).append(item_name)
        for word in re.findall(r"[a-z0-9]+", item_name.lower()):
            word_index.setdefault(word, []).append(item_name)

    partial_matches = [
        item_name
        for normalised_name, names in normalised_names.items()
        if query in normalised_name
        for item_name in names
    ]
    close_words = get_close_matches(
        query,
        list(word_index),
        n=8,
        cutoff=0.6,
    )
    word_matches = [
        item_name
        for close_word in close_words
        for item_name in word_index[close_word]
    ]
    close_keys = get_close_matches(
        query,
        list(normalised_names),
        n=8,
        cutoff=0.55,
    )
    close_matches = [
        item_name
        for close_key in close_keys
        for item_name in normalised_names[close_key]
    ]

    return list(dict.fromkeys(partial_matches + word_matches + close_matches))[:12]


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


def render_spotlight_assessment(assessment: dict) -> None:
    """Render the evidence and cautions attached to a spotlight selection."""

    confidence_color = {
        "High": "green",
        "Medium": "orange",
        "Low": "red",
    }[assessment["confidence"]]
    risk_color = {
        "Low": "green",
        "Medium": "orange",
        "High": "red",
    }[assessment["risk_level"]]

    st.badge(
        f"Confidence: {assessment['confidence']}",
        color=confidence_color,
    )
    st.badge(
        f"Risk: {assessment['risk_level']}",
        color=risk_color,
    )
    st.caption(assessment["explanation"])

    if assessment["risk_reasons"]:
        st.caption(
            "Risk factors: " + " ".join(assessment["risk_reasons"])
        )


comparison, market_summary, effect_summary, item_summary, metadata = load_dashboard()

apply_insights_styles()

page_header(
    "Market Insights",
    "Explainable market sentiment, risk flags, and opportunity screening from the latest comparison.",
)

if metadata is not None and metadata.get("snapshot_timestamp"):
    st.badge(
        f"Latest snapshot: {format_snapshot_timestamp(metadata['snapshot_timestamp'])}",
        color="blue",
    )

sentiment = calculate_market_sentiment(comparison)
risks = detect_market_risks(comparison)

with st.container(border=True):
    st.caption("Latest comparison summary")

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
                sentiment["label"],
                None,
            ),
            ("Confidence", sentiment["confidence"], None),
            ("Rising Markets", f"{sentiment['breadth_percent']:.1f}%", None),
            ("Median Movement", f"{sentiment['median_change_keys']:+.2f} keys", None),
        ])
        st.caption(
            f"Sentiment score: {sentiment['score']}/100. {sentiment['reason']}"
        )

st.divider()

overview_tab, opportunities_tab, spotlights_tab, historical_tab, lookup_tab = st.tabs([
    "Market Overview",
    "Opportunity Detector",
    "Effect & Item Spotlights",
    "Historical Comparison",
    "Find an Unusual",
])

with overview_tab:
    st.subheader("Market Narrative")

    for insight in generate_market_insights(comparison, market_summary):
        st.write(insight)

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
        "and meet the selected liquidity threshold. Longer periods screen for momentum "
        "instead of a single snapshot movement. This is not investment advice."
    )

    opportunity_history = load_history()
    opportunity_comparison = comparison

    if len(opportunity_history) >= 2:
        period_choice = st.selectbox(
            "Opportunity comparison period",
            options=["Latest snapshot pair", "All available snapshots"],
        )

        if period_choice == "All available snapshots":
            opportunity_comparison = compare_snapshots(
                opportunity_history.iloc[0]["source_file"],
                opportunity_history.iloc[-1]["source_file"],
            )

    maximum_listings = column_maximum(
        opportunity_comparison,
        "listings_new",
        fallback=3,
    )

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
        opportunity_comparison,
        minimum_listings=minimum_listings,
    )

    if opportunities.empty:
        st.info(
            "No markets increased in price over the selected period while meeting "
            "the liquidity and listing-supply conditions."
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

    effect_assessment = None
    if effect_spotlight is not None:
        effect_assessment = assess_spotlight(
            comparison,
            entity_column="effect_name",
            entity_name=effect_spotlight["effect_name"],
            represented_markets=int(effect_spotlight["unusuals"]),
            minimum_markets=minimum_markets,
            average_change=float(effect_spotlight["average_change"]),
        )

    item_assessment = None
    if item_spotlight is not None:
        item_assessment = assess_spotlight(
            comparison,
            entity_column="item_name",
            entity_name=item_spotlight["item_name"],
            represented_markets=int(item_spotlight["unusuals"]),
            minimum_markets=minimum_markets,
            average_change=float(item_spotlight["average_change"]),
        )

    effect_column, item_column = st.columns(2)

    with effect_column:
        st.markdown("#### Effect Spotlight")
        if effect_spotlight is None or effect_assessment["confidence"] == "Low":
            st.info(
                "Not enough supporting markets for a credible effect spotlight. "
                "Lower the threshold or collect more snapshots."
            )
        else:
            st.metric(
                effect_spotlight["effect_name"],
                f"{effect_spotlight['average_change']:+.2f} keys",
                f"{int(effect_spotlight['unusuals'])} markets represented",
            )
            render_spotlight_assessment(effect_assessment)
            for insight in generate_effect_insights(spotlight_effects):
                st.write(insight)

    with item_column:
        st.markdown("#### Item Spotlight")
        if item_spotlight is None or item_assessment["confidence"] == "Low":
            st.info(
                "Not enough supporting markets for a credible item spotlight. "
                "Lower the threshold or collect more snapshots."
            )
        else:
            st.metric(
                item_spotlight["item_name"],
                f"{item_spotlight['average_change']:+.2f} keys",
                f"{int(item_spotlight['unusuals'])} markets represented",
            )
            render_spotlight_assessment(item_assessment)
            for insight in generate_item_insights(spotlight_items):
                st.write(insight)

with historical_tab:
    st.subheader("Historical Comparison")
    st.caption(
        "Market-level price trends across every processed snapshot. "
        "A priced market represents an effect/item combination with a usable price."
    )

    history = load_history()

    if len(history) < 2:
        st.info("At least two processed snapshots are needed for historical comparison.")
    else:
        latest_timestamp = history["snapshot_timestamp"].max()
        period_options = {"All available snapshots": history}

        for label, days in (("Last 24 hours", 1), ("Last 3 days", 3), ("Last 7 days", 7)):
            window = history.loc[
                history["snapshot_timestamp"] >= latest_timestamp - pd.Timedelta(days=days)
            ]
            if len(window) >= 2:
                period_options[label] = window

        selected_period = st.selectbox(
            "Comparison period",
            options=list(period_options),
        )
        selected_history = period_options[selected_period].copy()
        start = selected_history.iloc[0]
        end = selected_history.iloc[-1]

        price_change_percent = (
            (end["median_price"] - start["median_price"])
            / start["median_price"]
            * 100
            if start["median_price"]
            else 0.0
        )
        market_change = int(end["priced_markets"] - start["priced_markets"])

        metric_row([
            ("Snapshots", len(selected_history), None),
            (
                "Median Price",
                f"{end['median_price']:.2f} keys",
                f"{price_change_percent:+.2f}%",
            ),
            (
                "Priced Markets",
                f"{int(end['priced_markets']):,}",
                f"{market_change:+,}",
            ),
            ("Period End", end["snapshot_timestamp"].strftime("%d %b %Y"), None),
        ])

        price_history = selected_history.melt(
            id_vars="snapshot_timestamp",
            value_vars=["median_price", "average_price"],
            var_name="Price measure",
            value_name="Keys",
        ).replace({
            "median_price": "Median price",
            "average_price": "Average price",
        })
        price_chart = px.line(
            price_history,
            x="snapshot_timestamp",
            y="Keys",
            color="Price measure",
            markers=True,
            template="plotly_dark",
        )
        price_chart.update_layout(
            title="Market Price Trend",
            xaxis_title="Snapshot",
            yaxis_title="Price (keys)",
            legend_title="",
        )
        st.plotly_chart(price_chart, use_container_width=True)

        market_chart = px.line(
            selected_history,
            x="snapshot_timestamp",
            y="priced_markets",
            markers=True,
            template="plotly_dark",
        )
        market_chart.update_layout(
            title="Priced Market Coverage",
            xaxis_title="Snapshot",
            yaxis_title="Priced markets",
            showlegend=False,
        )
        st.plotly_chart(market_chart, use_container_width=True)

        movers = compare_snapshots(start["source_file"], end["source_file"])
        movers = movers.dropna(subset=["percent_change"])

        st.subheader("Largest Movers in This Period")
        if movers.empty:
            st.info("No markets had comparable prices at both ends of this period.")
        else:
            mover_columns = [
                "effect_name",
                "item_name",
                "average_price_old",
                "average_price_new",
                "percent_change",
            ]
            gainers = movers.nlargest(5, "percent_change")[mover_columns].copy()
            losers = movers.nsmallest(5, "percent_change")[mover_columns].copy()

            for table in (gainers, losers):
                table["average_price_old"] = table["average_price_old"].map(
                    "{:.2f} keys".format
                )
                table["average_price_new"] = table["average_price_new"].map(
                    "{:.2f} keys".format
                )
                table["percent_change"] = table["percent_change"].map(
                    "{:+.2f}%".format
                )
                table.rename(columns={
                    "effect_name": "Effect",
                    "item_name": "Item",
                    "average_price_old": "Start Price",
                    "average_price_new": "End Price",
                    "percent_change": "Change",
                }, inplace=True)

            gainers_column, losers_column = st.columns(2)
            with gainers_column:
                st.markdown("#### Top Gainers")
                show_table(gainers)
            with losers_column:
                st.markdown("#### Top Losers")
                show_table(losers)

with lookup_tab:
    st.subheader("Find an Unusual")
    st.caption(
        "Choose an item and effect to see the price trend for that exact unusual market."
    )

    unusual_catalog = load_unusual_markets()

    if unusual_catalog.empty:
        st.info("No priced unusual markets are available to search yet.")
    else:
        item_options = unusual_catalog["item_name"].drop_duplicates().tolist()
        search_text = st.text_input(
            "Search for an item",
            placeholder="Type at least two letters, for example 'handy'",
            help="Search ignores capitalisation, spaces, and punctuation. Similar names are suggested, but you must choose the exact item.",
        )
        suggested_items = suggest_items(search_text, item_options)
        selected_item = None

        if len(normalise_search_text(search_text)) < 2:
            st.info("Type at least two letters to search for an item.")
        elif not suggested_items:
            st.info(
                "No item with a similar name appears in the latest snapshot. "
                "Try a shorter word or check the spelling."
            )
        else:
            st.caption("Choose the exact item from the suggestions below.")
            selected_item = st.selectbox(
                "Matching items",
                options=suggested_items,
                index=None,
                placeholder="Choose an item",
                key="unusual_item_choice",
            )

        if selected_item is not None:
            matching_unusuals = unusual_catalog.loc[
                unusual_catalog["item_name"].eq(selected_item)
            ].sort_values("effect_name")
            effect_options = matching_unusuals["effect_name"].tolist()
            selected_effect = st.selectbox(
                "Choose an unusual effect",
                options=effect_options,
            )
            selected_market = matching_unusuals.loc[
                matching_unusuals["effect_name"].eq(selected_effect)
            ].iloc[0]

            st.info(f"Viewing: {selected_effect} - {selected_item}")

            unusual_trend = load_unusual_market_trend(
                int(selected_market["effect_id"]),
                int(selected_market["defindex"]),
            )

            if unusual_trend.empty:
                st.info("This unusual market has no usable price history yet.")
            else:
                first_snapshot = unusual_trend.iloc[0]
                latest_snapshot = unusual_trend.iloc[-1]
                overall_change = (
                    (latest_snapshot["median_price"] - first_snapshot["median_price"])
                    / first_snapshot["median_price"]
                    * 100
                    if first_snapshot["median_price"]
                    else 0.0
                )
                previous_change = latest_snapshot["percent_change"]
                previous_change = 0.0 if pd.isna(previous_change) else previous_change

                if len(unusual_trend) >= 5:
                    confidence = "High"
                elif len(unusual_trend) >= 3:
                    confidence = "Medium"
                else:
                    confidence = "Low"

                volatility = unusual_trend["percent_change"].dropna().std(ddof=0)
                risk = (
                    "High" if confidence == "Low" or (not pd.isna(volatility) and volatility >= 25)
                    else "Medium" if not pd.isna(volatility) and volatility >= 10
                    else "Low"
                )
                trend_description = (
                    f"has risen {overall_change:+.1f}% across the saved snapshots"
                    if overall_change > 0
                    else f"has fallen {overall_change:+.1f}% across the saved snapshots"
                    if overall_change < 0
                    else "is unchanged across the saved snapshots"
                )

                st.subheader(f"{selected_effect} {selected_item}")
                st.caption(
                    f"This unusual {trend_description}. "
                    "Prices are shown in keys."
                )
                metric_row([
                    ("Latest Price", f"{latest_snapshot['median_price']:.2f} keys", None),
                    ("Change Since Previous", f"{previous_change:+.2f}%", None),
                    ("Snapshots Found", len(unusual_trend), None),
                    ("Confidence", confidence, None),
                ])

                if confidence == "Low":
                    st.warning(
                        "Not enough history for a reliable trend. Collect more snapshots "
                        "before treating this movement as meaningful."
                    )
                elif risk != "Low":
                    st.warning(
                        f"{risk} risk: this trend has large price swings between snapshots."
                    )

                unusual_chart = px.line(
                    unusual_trend,
                    x="snapshot_timestamp",
                    y="median_price",
                    markers=True,
                    template="plotly_dark",
                )
                unusual_chart.update_layout(
                    title="Price Trend",
                    xaxis_title="Snapshot",
                    yaxis_title="Median price (keys)",
                    showlegend=False,
                )
                st.plotly_chart(unusual_chart, use_container_width=True)

                with st.expander("See snapshot-by-snapshot prices"):
                    price_table = unusual_trend[
                        ["snapshot_timestamp", "median_price", "low_price", "high_price"]
                    ].copy()
                    price_table["snapshot_timestamp"] = price_table[
                        "snapshot_timestamp"
                    ].dt.strftime("%d %b %Y, %H:%M")
                    for column in ("median_price", "low_price", "high_price"):
                        price_table[column] = price_table[column].map(
                            "{:.2f} keys".format
                        )
                    price_table = price_table.rename(columns={
                        "snapshot_timestamp": "Snapshot",
                        "median_price": "Median Price",
                        "low_price": "Lowest Price",
                        "high_price": "Highest Price",
                    })
                    show_table(price_table)
