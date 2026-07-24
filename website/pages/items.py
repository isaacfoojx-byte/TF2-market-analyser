import streamlit as st
import plotly.express as px
from website.utils import load_items
from website.components import (
    page_header,
    metric_row,
    show_table,
    style_bar_chart,
)

st.set_page_config(
    page_title="Item Analytics",
    page_icon="📦",
    layout="wide",
)




_, item_summary = load_items()

page_header(
    "📦 Item Analytics",
    "Market statistics grouped by TF2 item.",
)

st.subheader("Summary")

total_items = item_summary["item_name"].nunique()

total_markets = int(
    item_summary["unusuals"].sum()
)

average_change = (
    item_summary["average_change"].mean()
)

best_item = item_summary.loc[
    item_summary["average_change"].idxmax(),
    "item_name",
]

metric_row([
    ("Items", total_items, None),
    ("Markets", total_markets, None),
    ("Average Change", f"{average_change:.2f}%", None),
    ("Top Item", best_item, None),
])

st.divider()

st.subheader("🏆 Item Leaderboard")

leaderboard = (
    item_summary
    .sort_values(
        "unusuals",
        ascending=False,
    )
)

show_table(leaderboard)

st.divider()

st.subheader("📈 Biggest Gainers")

gainers = (
    item_summary
    .sort_values(
        "average_change",
        ascending=False,
    )
    .head(10)
)

show_table(gainers)

st.divider()

st.subheader("📉 Biggest Losers")

losers = (
    item_summary
    .sort_values(
        "average_change",
        ascending=True,
    )
    .head(10)
)

show_table(losers)

st.divider()

st.subheader("📊 Listings by Item")

fig = px.bar(
    leaderboard.head(20),
    x="item_name",
    y="unusuals",
    text="unusuals",
)

fig = style_bar_chart(
    fig,
    "Item",
    "Markets",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)