import streamlit as st


def confidence_badge(confidence: str, explanation: str) -> None:
    """Render a confidence badge with a compact, expandable explanation."""

    color = {
        "High": "green",
        "Medium": "orange",
        "Low": "red",
    }.get(confidence, "gray")
    st.badge(f"Confidence: {confidence}", color=color)
    with st.popover(
        ":material/visibility:",
        help="Why this confidence level?",
    ):
        st.caption("Why this confidence level")
        st.write(explanation)


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
            confidence_badge(
                card["confidence"],
                card.get(
                    "confidence_reason",
                    "This confidence level reflects the amount and consistency of "
                    "the comparable market data behind this card.",
                ),
            )
        if card.get("risk") and card["risk"] != "Low":
            st.badge(
                f"Risk: {card['risk']}",
                color=risk_color,
            )

        st.caption(card["why"])

        if card.get("risk_reasons"):
            st.caption(f"Watch for: {card['risk_reasons'][0]}")
