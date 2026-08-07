import pandas as pd
import plotly.express as px
import streamlit as st

from insights import build_market_story
from website.components import metric_row, page_header, show_table, story_card
from website.utils import load_dashboard


st.set_page_config(page_title="Market Overview", page_icon="📈", layout="wide")

comparison, market_summary, effect_summary, item_summary, metadata = load_dashboard()

snapshot_caption = "A simple read on the latest TF2 unusual market snapshot."
if metadata is not None and metadata.get("snapshot_timestamp"):
    timestamp = pd.to_datetime(metadata["snapshot_timestamp"], errors="coerce")
    if not pd.isna(timestamp):
        snapshot_caption = (
            f"A simple read on the latest TF2 unusual market snapshot · "
            f"{timestamp:%d %b %Y, %H:%M}"
        )

page_header("📈 Market Overview", snapshot_caption)

story = build_market_story(comparison, market_summary)
story_card({
    "category": "Today’s market mood",
    "name": story["headline"],
    "headline": story["summary"],
    "confidence": story["confidence"],
    "risk": story["risk"],
    "why": "This combines the direction of comparable market prices with their typical movement.",
    "risk_reasons": story["risk_reasons"],
})

st.subheader("What players should notice")

falling_share = 100 - story.get("rising_markets", 0)
movement_card = {
    "category": "Price direction",
    "name": "Most markets are moving down" if falling_share >= 50 else "More markets are moving up",
    "headline": f"{max(falling_share, story.get('rising_markets', 0)):.1f}% moved in that direction",
    "confidence": story["confidence"],
    "risk": story["risk"],
    "why": "This looks at markets that had a price in both snapshots.",
    "risk_reasons": [],
}
typical_change = story.get("median_change_keys", 0)
movement_text = (
    f"Prices typically rose by {typical_change:.2f} keys"
    if typical_change > 0
    else f"Prices typically fell by {abs(typical_change):.2f} keys"
)
typical_card = {
    "category": "Typical movement",
    "name": "Small changes overall" if abs(typical_change) < 1 else "Noticeable price movement",
    "headline": movement_text,
    "confidence": story["confidence"],
    "risk": "Low" if abs(typical_change) < 1 else "Medium",
    "why": "The median is used so one very expensive unusual does not dominate the result.",
    "risk_reasons": [],
}
risk_message = (
    story["risk_reasons"][0]
    if story["risk_reasons"]
    else "No broad market warning was triggered in this comparison."
)
risk_card = {
    "category": "Keep an eye on",
    "name": "Market risk check",
    "headline": risk_message,
    "confidence": story["confidence"],
    "risk": story["risk"],
    "why": "Risk flags are warnings to investigate, not predictions of what happens next.",
    "risk_reasons": [],
}

for column, card in zip(st.columns(3), [movement_card, typical_card, risk_card]):
    with column:
        story_card(card)

with st.expander("Want the detailed market statistics?"):
    st.caption("Raw counts and price changes for players who want to dig deeper.")

    metric_row([
        ("Tracked Markets", f"{market_summary['total_unusuals']:,}", None),
        ("New Markets", int(market_summary["new_listings"]), None),
        ("Price Increases", int(market_summary["price_up"]), None),
        ("Price Decreases", int(market_summary["price_down"]), None),
    ])

    activity = pd.DataFrame({
        "Category": ["Price Up", "Price Down", "New", "Removed"],
        "Count": [
            market_summary["price_up"],
            market_summary["price_down"],
            market_summary["new_listings"],
            market_summary["removed"],
        ],
    })
    activity_chart = px.bar(activity, x="Category", y="Count", text="Count")
    activity_chart.update_traces(textposition="outside")
    activity_chart.update_layout(
        title="Detailed Market Activity",
        xaxis_title="",
        yaxis_title="Markets",
        showlegend=False,
        template="plotly_dark",
    )
    st.plotly_chart(activity_chart, use_container_width=True)

    st.markdown("#### Largest Movers")
    top_movers = (
        comparison.dropna(subset=["price_change"])
        .assign(abs_change=lambda frame: frame["price_change"].abs())
        .sort_values("abs_change", ascending=False)
        .head(10)
        [["item_name", "effect_name", "price_change", "listing_change", "status"]]
        .copy()
    )
    if top_movers.empty:
        st.info("No comparable price movements are available yet.")
    else:
        top_movers["price_change"] = top_movers["price_change"].map(
            "{:+.2f} keys".format
        )
        top_movers["listing_change"] = top_movers["listing_change"].fillna(0).map(
            "{:+.0f}".format
        )
        top_movers = top_movers.rename(columns={
            "item_name": "Item",
            "effect_name": "Effect",
            "price_change": "Price Change",
            "listing_change": "Listing Change",
            "status": "Status",
        })
        show_table(top_movers)
