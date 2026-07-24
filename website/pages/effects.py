import streamlit as st
import plotly.express as px

from website.utils import load_effects
from website.components import (
    page_header,
    metric_row,
    show_table,
    style_bar_chart,
)

st.set_page_config(
    page_title="Effect Analytics",
    page_icon="✨",
    layout="wide",
)


_, effect_summary = load_effects()

page_header(
    "✨ Effect Analytics",
    "Market statistics grouped by unusual effect.",
)

st.subheader("Summary")

total_effects = effect_summary["effect_name"].nunique()

total_markets = int(
    effect_summary["unusuals"].sum()
)

average_change = (
    effect_summary["average_change"].mean()
)

best_effect = effect_summary.loc[
    effect_summary["average_change"].idxmax(),
    "effect_name",
]

metric_row([
    ("Effects", total_effects, None),
    ("Markets", total_markets, None),
    ("Average Change", f"{average_change:.2f}%", None),
    ("Top Effect", best_effect, None),
])

st.divider()

st.subheader("🏆 Effect Leaderboard")

leaderboard = (
    effect_summary
    .sort_values(
        "unusuals",
        ascending=False,
    )
)

show_table(leaderboard)

st.divider()

st.subheader("📈 Biggest Gainers")

gainers = (
    effect_summary
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
    effect_summary
    .sort_values(
        "average_change",
        ascending=True,
    )
    .head(10)
)

show_table(losers)

st.divider()

st.subheader("📊 Top 20 Effects by Number of Markets")

st.caption(
    "The most active unusual effects based on the number of markets."
)

fig = px.bar(
    leaderboard.head(20),
    x="effect_name",
    y="unusuals",
    text="unusuals",
)

fig = style_bar_chart(fig,"Effect","Markets")

st.plotly_chart(
    fig,
    use_container_width=True,
)

