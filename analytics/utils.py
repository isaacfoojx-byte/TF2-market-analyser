from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
PRICE_COL = "bp_price_keys_equivalent"
PRICE_UNIT = "keys"

def load_data(csv_path):

    df = pd.read_csv(csv_path)

    priced = df[df["has_price"]].copy()

    return df, priced

def get_snapshots():

    snapshots = []

    pattern = re.compile(
        r"cleaned_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.csv"
    )

    for file in DATA_DIR.rglob("cleaned_*.csv"):
        if pattern.fullmatch(file.name):
            snapshots.append(file)

    return sorted(snapshots)

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
