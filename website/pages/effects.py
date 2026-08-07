import plotly.express as px
import streamlit as st

from insights import build_effect_cards
from website.components import page_header, show_table, story_card, style_bar_chart
from website.utils import load_effects


st.set_page_config(page_title="Effect Guide", page_icon="✨", layout="wide")

comparison, effect_summary = load_effects()

page_header(
    "✨ Effect Guide",
    "A simple view of which unusual effects are gaining attention, widely represented, or worth watching.",
)

st.subheader("Effects at a glance")
st.caption("These cards are a starting point for exploration, not investment advice.")

effect_cards = build_effect_cards(effect_summary, comparison)
if not effect_cards:
    st.info("Not enough effect data is available yet. Collect another priced snapshot and try again.")
else:
    for column, card in zip(st.columns(len(effect_cards)), effect_cards):
        with column:
            story_card(card)

with st.expander("Want the detailed effect statistics?"):
    st.caption("Full rankings for players who want the raw numbers.")

    leaderboard = effect_summary.sort_values("unusuals", ascending=False)
    detailed_leaderboard = leaderboard.rename(columns={
        "effect_name": "Effect",
        "unusuals": "Markets Represented",
        "average_change": "Average Change (keys)",
        "median_change": "Median Change (keys)",
        "average_listing_change": "Average Listing Change",
    })
    show_table(detailed_leaderboard)

    chart = px.bar(
        leaderboard.head(20),
        x="effect_name",
        y="unusuals",
        text="unusuals",
    )
    chart = style_bar_chart(chart, "Effect", "Markets represented")
    st.plotly_chart(chart, use_container_width=True)
