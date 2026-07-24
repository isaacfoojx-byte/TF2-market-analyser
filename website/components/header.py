import streamlit as st
# from website.components.header import page_header

def page_header(
    title: str,
    caption: str,
):
    st.title(title)
    st.caption(caption)

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