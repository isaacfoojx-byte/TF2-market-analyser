import streamlit as st


def story_card(card: dict) -> None:
    """Render a compact, player-facing insight card."""

    confidence_color = {
        "High": "green",
        "Medium": "orange",
        "Low": "red",
    }.get(card.get("confidence"), "gray")
    risk_color = {
        "Low": "green",
        "Medium": "orange",
        "High": "red",
    }.get(card.get("risk"), "gray")

    with st.container(border=True):
        st.caption(card["category"])
        st.subheader(card["name"])
        st.write(f"**{card['headline']}**")

        if card.get("confidence"):
            st.badge(
                f"Confidence: {card['confidence']}",
                color=confidence_color,
            )
        if card.get("risk"):
            st.badge(
                f"Risk: {card['risk']}",
                color=risk_color,
            )

        st.caption(card["why"])

        if card.get("risk_reasons"):
            st.caption(f"Watch for: {card['risk_reasons'][0]}")
