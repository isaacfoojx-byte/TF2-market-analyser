import streamlit as st

st.set_page_config(
    page_title="TFAnalytics",
    page_icon="🎩",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎩 TFAnalytics")

st.subheader("Team Fortress 2 Market Intelligence")

st.write(
    """
    Welcome to TFAnalytics!

    This platform provides analytics and insights into the Team Fortress 2
    unusual market using data collected from backpack.tf.
    """
)

st.divider()

st.header("🚧 Coming Soon")

st.markdown(
    """
    The dashboard is currently under development.

    Planned features:
    - 📈 Market Overview
    - 🔥 Top Movers
    - 🎩 Effect Analytics
    - 📦 Item Analytics
    - 📊 Historical Trends
    - 📄 Downloadable Reports
    """
)