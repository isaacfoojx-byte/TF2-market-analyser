import streamlit as st
from pathlib import Path


LOGO = Path(__file__).parent.parent / "assets" / "logo_transparent_2.png"


def page_header(title: str, caption: str) -> None:
    """Render one compact, consistent page header."""

    logo_column, title_column = st.columns([1, 4], vertical_alignment="center")

    with logo_column:
        st.image(str(LOGO), width=150)

    with title_column:
        st.title(title)
        st.caption(caption)

    st.divider()
