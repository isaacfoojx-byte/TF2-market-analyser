import streamlit as st
from pathlib import Path
import pandas as pd

st.set_page_config(
    page_title="Reports",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Reports")

st.caption(
    "Download generated reports and analytics."
)

REPORT_DIR = Path("data/comparisons")

csv_files = sorted(
    REPORT_DIR.glob("*.csv"),
    key=lambda f: f.name
)

if not csv_files:
    st.info("No reports have been generated yet.")
    st.stop()

report_info = []

for file in csv_files:

    report_info.append({
        "Report": file.name,
        "Size (KB)": round(file.stat().st_size / 1024, 1)
    })

st.subheader("Available Reports")

st.dataframe(
    pd.DataFrame(report_info),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Downloads")

for file in csv_files:
    with open(file, "rb") as f:
            st.download_button(
                label=f"📥 {file.name}",
                data=f,
                file_name=file.name,
                mime="text/csv",
            )
    

