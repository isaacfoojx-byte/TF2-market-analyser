import streamlit as st
from pathlib import Path
import base64


LOGO = Path(__file__).parent.parent / "assets" / "logo_transparent_2.png"


def page_header(title: str, caption: str) -> None:

    with open(LOGO, "rb") as image:
        encoded = base64.b64encode(image.read()).decode()

    st.markdown(
        f"""
    <div style="text-align:center;">
        <img src="data:image/png;base64,{encoded}" width="500">
        <h1>{title}</h1>
        <p>{caption}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.title(title)
    st.caption(caption)

    st.divider()
