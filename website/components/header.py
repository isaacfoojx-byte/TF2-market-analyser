import streamlit as st
from pathlib import Path
# from website.components.header import page_header

LOGO = Path(__file__).parent.parent / "assets" / "logo_transparent.png"

def page_header(
    title: str,
    caption: str,
    ) -> None: 
    """Display the common TFAnalytics page header."""
    
    left, centre, right = st.columns([1, 5, 1])

    with centre:
        st.image(
            LOGO,
            width=700,
        )

    st.title(title)
    st.caption(caption)
    st.divider()

# page_header(
#     "📈 Market Overview",
#     "Summary of the latest TF2 unusual market snapshot."
# )

# page_header(
#     "✨ Effect Analytics",
#     "Market statistics grouped by unusual effect."
# )

# page_header(
#     "📦 Item Analytics",
#     "Market statistics grouped by TF2 item."
# )

# page_header(
#     "📄 Reports",
#     "Download generated reports and analytics."
# )