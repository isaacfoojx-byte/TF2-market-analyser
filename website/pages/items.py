import streamlit as st
import plotly.express as px
from website.utils import load_items

st.set_page_config(
    page_title="Item Analytics",
    page_icon="📦",
    layout="wide",
)




comparison, item_summary = load_items()

st.title("📦 Item Analytics")

st.caption(
    "Market statistics grouped by TF2 item."
)

st.subheader("Summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Items",
    item_summary["item_name"].nunique(),
)

col2.metric(
    "Markets",
    int(item_summary["unusuals"].sum()),
)

col3.metric(
    "Average Change",
    f"{item_summary['average_change'].mean():.2f}%",
)

best_item = item_summary.loc[
    item_summary["average_change"].idxmax()
]

col4.metric(
    "Top Item",
    best_item["item_name"],
)

st.divider()

st.subheader("🏆 Item Leaderboard")

leaderboard = (
    item_summary
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
    item_summary
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
    item_summary
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

st.subheader("📊 Listings by Item")

fig = px.bar(
    leaderboard.head(20),
    x="item_name",
    y="unusuals",
    text="unusuals",
)

fig.update_traces(
    textposition="outside",
)

fig.update_layout(
    xaxis_title="Item",
    yaxis_title="Markets",
    showlegend=False,
    template="plotly_white",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)