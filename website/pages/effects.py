import streamlit as st
import plotly.express as px

from website.utils import load_effects

st.set_page_config(
    page_title="Effect Analytics",
    page_icon="✨",
    layout="wide",
)


comparison, effect_summary = load_effects()

st.title("✨ Effect Analytics")

st.caption(
    "Market statistics grouped by unusual effect."
)

st.subheader("Summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Effects",
    effect_summary["effect_name"].nunique(),
)

col2.metric(
    "Markets",
    int(effect_summary["unusuals"].sum()),
)

col3.metric(
    "Average Change",
    f"{effect_summary['average_change'].mean():.2f}%",
)

best_effect = effect_summary.loc[
    effect_summary["average_change"].idxmax()
]

col4.metric(
    "Top Effect",
    best_effect["effect_name"],
)

st.divider()

st.subheader("🏆 Effect Leaderboard")

leaderboard = (
    effect_summary
    .sort_values(
        "unusuals",
        ascending=False,
    )
)

st.dataframe(
    leaderboard,
    use_container_width=True,
    hide_index=True,
)

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

st.dataframe(
    gainers,
    use_container_width=True,
    hide_index=True,
)

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

st.dataframe(
    losers,
    use_container_width=True,
    hide_index=True,
)

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

fig.update_traces(
    textposition="outside",
)

fig.update_layout(
    xaxis_title="Effect",
    yaxis_title="Markets",
    showlegend=False,
    template="plotly_white",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)