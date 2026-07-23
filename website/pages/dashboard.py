import streamlit as st
import plotly.express as px

from analytics.snapshot_comparison import (
    build_comparison,
    calculate_changes,
    classify_changes,
    build_market_summary,
    build_effect_summary,
    build_item_summary
)

# In order to run this website, type this command in VSCode: python -m streamlit run website/app.py

@st.cache_data
def load_market():
    comparison = build_comparison()
    comparison = calculate_changes(comparison)
    comparison = classify_changes(comparison)

    market_summary = build_market_summary(comparison)
    effect_summary = build_effect_summary(comparison)
    item_summary = build_item_summary(comparison)

    return comparison, market_summary, effect_summary, item_summary

st.set_page_config(
    page_title="Market Overview",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Market Overview")

comparison, market_summary, effect_summary, item_summary = load_market()

summary = market_summary.iloc[0]

activity = {
    "Category": [
        "Price Up",
        "Price Down",
        "New",
        "Removed",
    ],
    "Count": [
        summary["price_up"],
        summary["price_down"],
        summary["new_listings"],
        summary["removed"],
    ],
}

st.subheader("Summary")

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

st.subheader("📊 Market Activity")

fig = px.bar(
    activity,
    x="Category",
    y="Count",
    text="Count",
)

fig.update_layout(
    xaxis_title="",
    yaxis_title="Number of Listings",
    showlegend=False,
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("🔥 Top Movers")

st.caption("Largest percentage price movements since the previous snapshot.")

top_movers = (
    comparison
    .assign(abs_change=comparison["price_change"].abs())
    .sort_values("abs_change", ascending=False)
    .head(10)
)

columns = [
    "item_name",
    "effect_name",
    "price_change",
    "listing_change",
    "status",
]

st.dataframe(
    top_movers[columns],
    use_container_width=True,
    hide_index=True,
)

effect_summary = (
    effect_summary
    .sort_values("unusuals", ascending=False)
    .head(10)
)

st.divider()

st.subheader("✨ Effect Summary")

st.caption("Top effects ranked by number of unusual listings.")

st.dataframe(
    effect_summary,
    use_container_width=True,
    hide_index=True,
)

item_summary = (
    item_summary
    .sort_values("unusuals", ascending=False)
    .head(10)
)

st.divider()

st.subheader("📦 Item Summary")

st.caption("Top items ranked by number of unusual listings.")

st.dataframe(
    item_summary,
    use_container_width=True,
    hide_index=True,
)

