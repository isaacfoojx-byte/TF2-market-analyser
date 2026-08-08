import plotly.express as px
import streamlit as st

from insights import build_effect_cards
from website.components import page_header, show_table, story_card, style_bar_chart
from website.item_images import effect_icon_html
from website.utils import load_effects


st.set_page_config(page_title="Effect Guide", layout="wide")

comparison, effect_summary = load_effects()

page_header(
    "Effect Guide",
    "A simple view of which unusual effects are gaining attention, widely represented, or worth watching.",
)

st.subheader("Effects at a glance")
st.caption("These cards are a starting point for exploration, not investment advice.")

effect_cards = build_effect_cards(effect_summary, comparison)
if not effect_cards:
    st.info("Not enough effect data is available yet. Collect another priced snapshot and try again.")
else:
    # The cards summarise one effect across many hats, so show the effect's
    # particle icon instead of suggesting that a particular hat is featured.
    effect_ids = {}
    if {"effect_name", "effect_id"}.issubset(comparison.columns):
        effect_ids = (
            comparison[["effect_name", "effect_id"]]
            .dropna()
            .drop_duplicates("effect_name")
            .set_index("effect_name")["effect_id"]
            .to_dict()
        )

    for card in effect_cards:
        effect_id = effect_ids.get(card["name"])
        if effect_id is not None:
            preview = effect_icon_html(
                int(effect_id),
                card["name"],
                width=56,
            )
            if preview:
                card["image_html"] = preview

    story_card(effect_cards[0])

    st.subheader("What else to notice")
    for column, card in zip(st.columns(2), effect_cards[1:]):
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
