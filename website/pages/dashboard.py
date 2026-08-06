import streamlit as st
import plotly.express as px
import pandas as pd
from website.utils import load_dashboard
from website.components import (
    page_header,
    metric_row,
    show_table,
)

# In order to run this website, type this command in VSCode: python -m streamlit run website/app.py



st.set_page_config(
    page_title="Market Overview",
    page_icon="📈",
    layout="wide"
)


comparison, market_summary, effect_summary, item_summary, metadata = load_dashboard()


if metadata is not None:
    snapshot_time = pd.to_datetime(
        metadata["snapshot_timestamp"]
    )

    caption = (
        f"Summary of the latest TF2 unusual market snapshot.\n\n"
        f"Market snapshot: {snapshot_time:%d %b %Y %H:%M}"
    )
else:
    caption = (
        "Summary of the latest TF2 unusual market snapshot."
    )

page_header(
    "📈 Market Overview",
    caption,
)



summary = market_summary

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

metric_row([
    ("🎩 Markets", f"{summary['total_unusuals']:,}", None),
    ("🆕 New Listings", int(summary["new_listings"]), None),
    ("📈 Price Increases", int(summary["price_up"]), None),
    ("📉 Price Decreases", int(summary["price_down"]), None),
])
st.divider()

metric_row([
    ("Average Change", f"{summary['average_change']:.2f}", None),
    ("Median Change", f"{summary['median_change']:.2f}", None),
    ("Unchanged", int(summary["unchanged"]), None),
])

st.divider()

st.subheader("📊 Market Activity")

fig = px.bar(
    activity,
    x="Category",
    y="Count",
    text="Count",
)

fig.update_traces(
    textposition="outside",
)

fig.update_layout(
    xaxis_title="",
    yaxis_title="Number of Listings",
    showlegend=False,
    template="plotly_white",
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

top_mover_columns = [
    "item_name",
    "effect_name",
    "price_change",
    "listing_change",
    "status",
]

top_movers = top_movers[top_mover_columns].copy()

top_movers["price_change"] = (
    top_movers["price_change"]
    .map("{:+.2f}".format)
)

top_movers["listing_change"] = (
    top_movers["listing_change"]
    .astype(int)
    .map("{:+d}".format)
)

show_table(top_movers)

effect_summary = (
    effect_summary
    .sort_values("unusuals", ascending=False)
    .head(10)
)

st.divider()

st.subheader("✨ Effect Summary")

st.caption("Top effects ranked by number of unusual listings.")

show_table(effect_summary)

item_summary = (
    item_summary
    .sort_values("unusuals", ascending=False)
    .head(10)
)

st.divider()

st.subheader("📦 Item Summary")

st.caption("Top items ranked by number of unusual listings.")

show_table(item_summary)