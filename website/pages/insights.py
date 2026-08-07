from difflib import get_close_matches
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.history import compare_snapshots
from analytics.community_history import compare_community_snapshots
from insights import (
    calculate_market_sentiment,
    detect_market_risks,
    find_opportunities,
    generate_effect_insights,
    generate_item_insights,
    generate_market_insights,
)
from insights.common import assess_spotlight
from website.components import confidence_badge, metric_row, page_header, show_table
from website.utils import (
    load_community_market_trend,
    load_community_markets,
    load_community_price_history,
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


def craftability_label(craftable: bool | None) -> str:
    """Show nullable craftability values as clear player-facing labels."""

    if craftable is None or pd.isna(craftable):
        return "Craftability not listed"
    return "Craftable" if bool(craftable) else "Non-craftable"


def community_confidence(snapshot_count: int) -> str:
    if snapshot_count >= 5:
        return "High"
    if snapshot_count >= 3:
        return "Medium"
    return "Low"


def snapshot_confidence_reason(snapshot_count: int) -> str:
    """Explain the common confidence thresholds used by item trend lookups."""

    return (
        f"This trend has {snapshot_count} saved snapshot"
        f"{'s' if snapshot_count != 1 else ''}. High confidence needs at least 5 "
        "snapshots; medium confidence needs at least 3."
    )


def format_community_price(value: float, unit: str | None) -> str:
    """Format one community guide value in backpack.tf-style ref or keys."""

    if pd.isna(value) or not unit:
        return "Not listed"
    return f"{value:.2f} {unit}"


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


def missing_required_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
) -> list[str]:
    """Return missing columns instead of letting an older dataset crash the page."""

    return sorted(required_columns.difference(dataframe.columns))


def render_spotlight_assessment(assessment: dict) -> None:
    """Render the evidence and cautions attached to a spotlight selection."""

    risk_color = {
        "Low": "green",
        "Medium": "orange",
        "High": "red",
    }[assessment["risk_level"]]

    confidence_badge(
        assessment["confidence"],
        assessment["confidence_reason"],
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
        confidence_badge(sentiment["confidence"], sentiment["reason"])
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
        confidence_badge(
            sentiment["confidence"],
            f"{sentiment['comparable_markets']:,} markets had usable prices in both "
            "snapshots. High confidence needs at least 100 comparable markets; "
            "medium confidence needs at least 25.",
        )

st.divider()

(
    overview_tab,
    opportunities_tab,
    spotlights_tab,
    historical_tab,
    community_overview_tab,
    lookup_tab,
    community_lookup_tab,
) = st.tabs([
    "Market Overview",
    "Opportunity Detector",
    "Effect & Item Spotlights",
    "Historical Comparison",
    "Community Guide",
    "Find an Unusual",
    "Find a Community Item",
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

with community_overview_tab:
    st.subheader("Community Price Guide")
    st.caption(
        "History from backpack.tf's community price guide. These values are not live "
        "listing prices, supply, or sales volume. Refined-metal values are converted "
        "using the key price captured with each snapshot."
    )

    community_history = load_community_price_history()
    required_history_columns = {
        "snapshot_timestamp",
        "source_file",
        "priced_variants",
        "unique_items",
        "median_price_keys",
        "average_price_keys",
        "key_price_ref",
    }
    missing_history_columns = missing_required_columns(
        community_history,
        required_history_columns,
    )
    if community_history.empty:
        st.info(
            "No cleaned community price snapshots are available yet. Run the community "
            "spreadsheet scraper and cleaner first."
        )
    elif missing_history_columns:
        st.warning(
            "Community guide data uses an older format and cannot be shown safely. "
            "Re-run the community cleaner (or collect a new community scrape) after "
            "deploying the current code."
        )
    else:
        latest_community = community_history.iloc[-1]
        metric_row([
            ("Price Guide Entries", f"{int(latest_community['priced_variants']):,}", None),
            ("Different Items", f"{int(latest_community['unique_items']):,}", None),
            ("Median Item Value", f"{latest_community['median_price_keys']:.2f} keys", None),
            ("Conversion Rate", f"{latest_community['key_price_ref']:.2f} ref", None),
            ("Latest Update", latest_community["snapshot_timestamp"].strftime("%d %b %Y"), None),
        ])

        if len(community_history) < 2:
            st.warning(
                "One guide snapshot is saved. Collect another snapshot to show price movement."
            )
        else:
            first_community = community_history.iloc[0]
            guide_change_percent = (
                (latest_community["median_price_keys"] - first_community["median_price_keys"])
                / first_community["median_price_keys"]
                * 100
                if first_community["median_price_keys"]
                else 0.0
            )
            st.caption(
                f"The typical guide price changed {guide_change_percent:+.2f}% across "
                f"{len(community_history)} saved snapshots."
            )

            guide_prices = community_history.melt(
                id_vars="snapshot_timestamp",
                value_vars=["median_price_keys", "average_price_keys"],
                var_name="Price measure",
                value_name="Keys",
            ).replace({
                "median_price_keys": "Typical guide price",
                "average_price_keys": "Average guide price",
            })
            guide_chart = px.line(
                guide_prices,
                x="snapshot_timestamp",
                y="Keys",
                color="Price measure",
                markers=True,
                template="plotly_dark",
            )
            guide_chart.update_layout(
                title="Community Guide Price Trend",
                xaxis_title="Snapshot",
                yaxis_title="Keys",
                legend_title="",
            )
            st.plotly_chart(guide_chart, use_container_width=True)

            movers = compare_community_snapshots(
                first_community["source_file"],
                latest_community["source_file"],
            ).dropna(subset=["percent_change"])
            st.subheader("Largest Guide Price Changes")
            if movers.empty:
                st.info("No item variants have usable prices at both ends of this period.")
            else:
                def prepare_community_movers(dataframe: pd.DataFrame) -> pd.DataFrame:
                    table = dataframe[[
                        "item_name",
                        "quality",
                        "craftable",
                        "guide_price_keys_old",
                        "guide_price_keys_new",
                        "percent_change",
                    ]].copy()
                    table["craftable"] = table["craftable"].map(craftability_label)
                    table["guide_price_keys_old"] = table["guide_price_keys_old"].map(
                        "{:.2f} keys".format
                    )
                    table["guide_price_keys_new"] = table["guide_price_keys_new"].map(
                        "{:.2f} keys".format
                    )
                    table["percent_change"] = table["percent_change"].map("{:+.2f}%".format)
                    return table.rename(columns={
                        "item_name": "Item",
                        "quality": "Quality",
                        "craftable": "Variant",
                        "guide_price_keys_old": "Start Guide Price",
                        "guide_price_keys_new": "Latest Guide Price",
                        "percent_change": "Guide Price Change",
                    })

                gainers_column, losers_column = st.columns(2)
                with gainers_column:
                    st.markdown("#### Largest Increases")
                    show_table(prepare_community_movers(movers.nlargest(5, "percent_change")))
                with losers_column:
                    st.markdown("#### Largest Decreases")
                    show_table(prepare_community_movers(movers.nsmallest(5, "percent_change")))

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

                confidence_badge(
                    confidence,
                    snapshot_confidence_reason(len(unusual_trend)),
                )

                if latest_snapshot.get("price_is_range", False):
                    st.warning(
                        "Range-based guide price: backpack.tf lists "
                        f"{latest_snapshot['source_price_low']:.2f}"
                        f"–{latest_snapshot['source_price_high']:.2f} "
                        f"{latest_snapshot['source_price_unit']}. "
                        "The displayed value is the midpoint of that range."
                    )

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

with community_lookup_tab:
    st.subheader("Find a Community Item")
    st.caption(
        "Search the backpack.tf community price guide for one exact item variant. "
        "Guide prices are shown in keys and are not current listings or sale prices."
    )

    community_catalog = load_community_markets()
    if community_catalog.empty:
        st.info(
            "No cleaned community guide data is available yet. Run a spreadsheet scrape "
            "and clean its CSV before searching."
        )
    else:
        community_item_options = community_catalog["item_name"].drop_duplicates().tolist()
        community_search_text = st.text_input(
            "Search for a community item",
            placeholder="Type at least two letters, for example 'captain'",
            help="Search ignores capitalisation, spaces, and punctuation. Choose an exact item before viewing its guide history.",
            key="community_item_search",
        )
        suggested_community_items = suggest_items(
            community_search_text,
            community_item_options,
        )
        selected_community_item = None

        if len(normalise_search_text(community_search_text)) < 2:
            st.info("Type at least two letters to search for an item.")
        elif not suggested_community_items:
            st.info(
                "No similar item appears in the latest community guide snapshot. "
                "Try a shorter word or check the spelling."
            )
        else:
            st.caption("Choose the exact item from the suggestions below.")
            selected_community_item = st.selectbox(
                "Matching community items",
                options=suggested_community_items,
                index=None,
                placeholder="Choose an item",
                key="community_item_choice",
            )

        if selected_community_item is not None:
            matching_variants = community_catalog.loc[
                community_catalog["item_name"].eq(selected_community_item)
            ].copy()
            matching_variants["variant_label"] = matching_variants.apply(
                lambda row: (
                    f"{row['quality']} - {craftability_label(row['craftable'])}"
                ),
                axis=1,
            )
            variant_index = st.selectbox(
                "Choose a quality and variant",
                options=matching_variants.index.tolist(),
                format_func=lambda index: matching_variants.loc[index, "variant_label"],
                key="community_variant_choice",
            )
            selected_variant = matching_variants.loc[variant_index]
            selected_craftable = (
                None
                if pd.isna(selected_variant["craftable"])
                else bool(selected_variant["craftable"])
            )
            community_trend = load_community_market_trend(
                selected_community_item,
                str(selected_variant["quality"]),
                selected_craftable,
            )

            st.info(
                f"Viewing guide price: {selected_community_item} - "
                f"{selected_variant['variant_label']}"
            )

            if community_trend.empty:
                st.info("This item variant has no usable community guide history yet.")
            elif missing_required_columns(
                community_trend,
                {
                    "snapshot_timestamp",
                    "median_price_keys",
                    "median_price_usd",
                    "display_price",
                    "display_unit",
                    "percent_change",
                    "stats_url",
                    "price_is_range",
                    "source_price_low",
                    "source_price_high",
                    "source_price_unit",
                },
            ):
                st.warning(
                    "This community snapshot uses an older format. Re-run the community "
                    "cleaner after deploying the current code, then refresh this page."
                )
            else:
                first_snapshot = community_trend.iloc[0]
                latest_snapshot = community_trend.iloc[-1]
                overall_change = (
                    (latest_snapshot["median_price_keys"] - first_snapshot["median_price_keys"])
                    / first_snapshot["median_price_keys"]
                    * 100
                    if first_snapshot["median_price_keys"]
                    else 0.0
                )
                previous_change = latest_snapshot["percent_change"]
                previous_change = 0.0 if pd.isna(previous_change) else previous_change
                confidence = community_confidence(len(community_trend))
                volatility = community_trend["percent_change"].dropna().std(ddof=0)
                movement = (
                    "Large swings" if not pd.isna(volatility) and volatility >= 15
                    else "Changing" if not pd.isna(volatility) and volatility >= 5
                    else "Stable"
                )

                usd_value = latest_snapshot["median_price_usd"]
                usd_label = (
                    f"${usd_value:.2f}"
                    if not pd.isna(usd_value)
                    else "Not listed"
                )
                st.caption(
                    f"The saved guide price has changed {overall_change:+.1f}% across "
                    f"{len(community_trend)} snapshots."
                )
                metric_row([
                    (
                        "Latest Guide Price",
                        format_community_price(
                            latest_snapshot["display_price"],
                            latest_snapshot["display_unit"],
                        ),
                        None,
                    ),
                    ("Approximate USD", usd_label, None),
                    ("Guide Price Movement", movement, f"{previous_change:+.2f}% last update"),
                    ("Confidence", confidence, None),
                ])

                confidence_badge(
                    confidence,
                    snapshot_confidence_reason(len(community_trend)),
                )

                if latest_snapshot["price_is_range"]:
                    st.warning(
                        "Range-based guide price: backpack.tf lists "
                        f"{latest_snapshot['source_price_low']:.2f} to "
                        f"{latest_snapshot['source_price_high']:.2f} "
                        f"{latest_snapshot['source_price_unit']}. "
                        "The displayed value is the midpoint of that range."
                    )

                if confidence == "Low":
                    st.warning(
                        "Not enough saved guide snapshots for a reliable trend. "
                        "Collect more updates before reading much into this change."
                    )
                elif movement == "Large swings":
                    st.warning(
                        "Guide values changed sharply between saved snapshots. Check the "
                        "source page and treat the trend cautiously."
                    )

                guide_trend_chart = px.line(
                    community_trend,
                    x="snapshot_timestamp",
                    y="median_price_keys",
                    markers=True,
                    template="plotly_dark",
                )
                guide_trend_chart.update_layout(
                    title="Community Guide Price Trend",
                    xaxis_title="Snapshot",
                    yaxis_title="Guide price (keys)",
                    showlegend=False,
                )
                st.plotly_chart(guide_trend_chart, use_container_width=True)

                stats_url = latest_snapshot["stats_url"]
                if isinstance(stats_url, str) and stats_url:
                    st.link_button("Open this item on backpack.tf", stats_url)

                with st.expander("See saved guide prices"):
                    guide_table = community_trend[[
                        "snapshot_timestamp",
                        "display_price",
                        "display_unit",
                        "median_price_usd",
                    ]].copy()
                    guide_table["snapshot_timestamp"] = guide_table[
                        "snapshot_timestamp"
                    ].dt.strftime("%d %b %Y, %H:%M")
                    guide_table["Guide Price"] = guide_table.apply(
                        lambda row: format_community_price(
                            row["display_price"],
                            row["display_unit"],
                        ),
                        axis=1,
                    )
                    guide_table["median_price_usd"] = guide_table[
                        "median_price_usd"
                    ].map(lambda value: f"${value:.2f}" if not pd.isna(value) else "Not listed")
                    guide_table = guide_table.rename(columns={
                        "snapshot_timestamp": "Snapshot",
                        "median_price_usd": "Approximate USD",
                    })[["Snapshot", "Guide Price", "Approximate USD"]]
                    show_table(guide_table)
