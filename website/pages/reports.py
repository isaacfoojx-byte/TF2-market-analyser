import streamlit as st
import pandas as pd

from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from website.components import page_header


st.set_page_config(
    page_title="Downloads",
    layout="wide",
)

page_header(
    "Downloads",
    "Browse and download historical TF2 market snapshots.",
)

# ------------------------------------------------------------------
# Choose dataset
# ------------------------------------------------------------------

@dataclass(frozen=True)
class DatasetLocation:
    data_dir: Path
    pattern: str
    timestamp_prefix: str


MARKETS = {
    "Unusual Market": {
        "Processed": DatasetLocation(
            Path("data/processed"), "cleaned_*.csv", "cleaned_"
        ),
        "Raw": DatasetLocation(
            Path("data/raw"), "unusuals_*.csv", "unusuals_"
        ),
    },
    "Community Price Guide": {
        "Processed": DatasetLocation(
            Path("data/community/processed"),
            "community_prices_*.csv",
            "community_prices_",
        ),
        "Raw": DatasetLocation(
            Path("data/community/raw"),
            "community_prices_*.csv",
            "community_prices_",
        ),
    },
}

market_name = st.radio(
    "Market",
    list(MARKETS),
    horizontal=True,
)
dataset_type = st.radio(
    "Dataset",
    ["Processed", "Raw"],
    horizontal=True,
)

dataset = MARKETS[market_name][dataset_type]

files = sorted(
    dataset.data_dir.glob(dataset.pattern),
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

timestamp = latest.stem.removeprefix(dataset.timestamp_prefix)
snapshot = datetime.strptime(
    timestamp,
    "%Y-%m-%d_%H-%M-%S",
)

st.subheader(f"Latest {market_name} Snapshot")

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
        "Download Latest Dataset",
        f,
        file_name=latest.name,
        mime="text/csv",
        key=f"latest-{market_name}-{dataset_type}-{latest.name}",
        use_container_width=True,
    )

st.divider()

# ------------------------------------------------------------------
# Historical snapshots
# ------------------------------------------------------------------

st.subheader("Historical Snapshots")

for file in files:

    df = pd.read_csv(file)

    timestamp = file.stem.removeprefix(dataset.timestamp_prefix)

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
                    key=f"{market_name}-{dataset_type}-{file.name}",
                    use_container_width=True,
                )
