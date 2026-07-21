from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

def load_data(csv_path):

    df = pd.read_csv(csv_path)

    priced = df[df["has_price"]].copy()

    return df, priced

def get_snapshots():

    snapshots = sorted(
        DATA_DIR.glob("cleaned_*.csv")
    )

    return snapshots

def load_latest_data():

    latest = get_snapshots()[-1]

    print(f"Loading {latest.name}")

    return load_data(latest)

def get_latest_pair():

    snapshots = get_snapshots()

    if len(snapshots) < 2:
        raise ValueError(
            "Need at least two snapshots."
        )

    return snapshots[-2], snapshots[-1]