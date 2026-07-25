import streamlit as st
import pandas as pd

from pathlib import Path
from datetime import datetime

from website.components import page_header


st.set_page_config(
    page_title="Downloads",
    page_icon="📁",
    layout="wide",
)

page_header(
    "📁 Downloads",
    "Browse and download historical TF2 market snapshots.",
)

# ------------------------------------------------------------------
# Choose dataset type
# ------------------------------------------------------------------

dataset_type = st.radio(
    "Dataset",
    ["Processed", "Raw"],
    horizontal=True,
)

if dataset_type == "Processed":
    DATA_DIR = Path("data/processed")
    pattern = "cleaned_*.csv"
else:
    DATA_DIR = Path("data/raw")
    pattern = "unusuals_*.csv"

files = sorted(
    DATA_DIR.glob(pattern),
    reverse=True,
)

if not files:
    st.warning("No datasets found.")
    st.stop()

# ------------------------------------------------------------------
# Latest snapshot
# ------------------------------------------------------------------

latest = files[0]
latest_df = pd.read_csv(latest)

timestamp = latest.stem.split("_", 1)[1]
snapshot = datetime.strptime(
    timestamp,
    "%Y-%m-%d_%H-%M-%S",
)

st.subheader("📌 Latest Snapshot")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Snapshot",
    snapshot.strftime("%d %b %Y"),
)

col2.metric(
    "Time",
    snapshot.strftime("%H:%M"),
)

col3.metric(
    "Rows",
    f"{len(latest_df):,}",
)

with open(latest, "rb") as f:
    st.download_button(
        "⬇ Download Latest Dataset",
        f,
        file_name=latest.name,
        mime="text/csv",
        use_container_width=True,
    )

st.divider()

# ------------------------------------------------------------------
# Historical snapshots
# ------------------------------------------------------------------

st.subheader("📜 Historical Snapshots")

for file in files:

    df = pd.read_csv(file)

    timestamp = file.stem.split("_", 1)[1]

    snapshot = datetime.strptime(
        timestamp,
        "%Y-%m-%d_%H-%M-%S",
    )

    with st.container(border=True):

        left, right = st.columns([4, 1])

        with left:

            st.markdown(
                f"### {snapshot.strftime('%d %b %Y %H:%M')}"
            )

            st.write(f"**Filename:** `{file.name}`")

            st.write(f"**Rows:** {len(df):,}")

            st.write(
                f"**Size:** {file.stat().st_size / 1024:.1f} KB"
            )

        with right:

            with open(file, "rb") as f:

                st.download_button(
                    "Download",
                    f,
                    file_name=file.name,
                    mime="text/csv",
                    key=file.name,
                    use_container_width=True,
                )
