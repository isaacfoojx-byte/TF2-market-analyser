import plotly.express as px
import streamlit as st

from insights import build_item_cards
from website.components import page_header, show_table, story_card, style_bar_chart
from website.utils import load_items


st.set_page_config(page_title="Item Guide", page_icon="📦", layout="wide")

comparison, item_summary = load_items()

page_header(
    "📦 Item Guide",
    "A simple view of which unusual items are gaining attention, widely represented, or worth watching.",
)

st.subheader("Items at a glance")
st.caption("These cards are a starting point for exploration, not investment advice.")

item_cards = build_item_cards(item_summary, comparison)
if not item_cards:
    st.info("Not enough item data is available yet. Collect another priced snapshot and try again.")
else:
    for column, card in zip(st.columns(len(item_cards)), item_cards):
        with column:
            story_card(card)

with st.expander("Want the detailed item statistics?"):
    st.caption("Full rankings for players who want the raw numbers.")

    leaderboard = item_summary.sort_values("unusuals", ascending=False)
    detailed_leaderboard = leaderboard.rename(columns={
        "item_name": "Item",
        "unusuals": "Markets Represented",
        "average_change": "Average Change (keys)",
        "median_change": "Median Change (keys)",
        "average_listing_change": "Average Listing Change",
    })
    show_table(detailed_leaderboard)

    chart = px.bar(
        leaderboard.head(20),
        x="item_name",
        y="unusuals",
        text="unusuals",
    )
    chart = style_bar_chart(chart, "Item", "Markets represented")
    st.plotly_chart(chart, use_container_width=True)
