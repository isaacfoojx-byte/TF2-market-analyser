import streamlit as st
from pathlib import Path

LOGO = (
    Path(__file__).parent
    / "website"
    / "assets"
    / "logo_only.png"
)

st.set_page_config(
    page_title="TFAnalytics",
    page_icon=str(LOGO),
    layout="wide",
    initial_sidebar_state="expanded"
)

home = st.Page(
    "website/pages/home.py",
    title="Home",
)

dashboard = st.Page(
    "website/pages/dashboard.py",
    title="Dashboard",
)

insights = st.Page(
    "website/pages/insights.py",
    title="Insights",
)

effects = st.Page(
    "website/pages/effects.py",
    title="Effects",
)

items = st.Page(
    "website/pages/items.py",
    title="Items",
)

downloads = st.Page(
    "website/pages/reports.py",
    title="Downloads",
)

pg = st.navigation([
    home,
    dashboard,
    insights,
    effects,
    items,
    downloads,
])

pg.run()
