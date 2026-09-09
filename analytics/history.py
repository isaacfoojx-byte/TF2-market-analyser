"""Historical market summaries and comparisons built from processed snapshots."""

from pathlib import Path

import pandas as pd

from analytics.utils import PRICE_COL, get_snapshots, load_data
from analytics.comparison import compare_files, prepare_markets


MARKET_KEYS = ["effect_id", "effect_name", "defindex", "item_name"]


def history_signature() -> tuple[tuple[str, int, int], ...]:
    """Describe the available snapshots so cached UI data refreshes after a scrape."""

    return tuple(
        (snapshot.name, snapshot.stat().st_mtime_ns, snapshot.stat().st_size)
        for snapshot in get_snapshots()
    )


def _snapshot_timestamp(snapshot_file: Path, dataframe: pd.DataFrame) -> pd.Timestamp:
    """Read the scrape timestamp, falling back to the timestamp in the filename."""

    if "scrape_timestamp" in dataframe.columns:
        timestamps = pd.to_datetime(dataframe["scrape_timestamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
        if timestamps.notna().any():
            return timestamps.dropna().iloc[0]

    return pd.to_datetime(
        snapshot_file.stem.removeprefix("cleaned_"),
        format="%Y-%m-%d_%H-%M-%S",
    )


def _aggregate_snapshot(priced: pd.DataFrame) -> pd.DataFrame:
    """Aggregate individual rows into comparable effect/item markets."""

    return prepare_markets(priced, "unusual").dropna(subset=["average_price"])


def load_market_history() -> pd.DataFrame:
    """Return one aggregate row for every valid processed snapshot."""

    records: list[dict] = []

    for snapshot_file in get_snapshots():
        dataframe, priced = load_data(snapshot_file)

        if priced.empty:
            continue

        markets = _aggregate_snapshot(priced)
        market_count = len(markets)
        records.append({
            "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
            "source_file": str(snapshot_file),
            "priced_markets": market_count,
            "priced_rows": len(priced),
            "unique_effects": priced["effect_name"].nunique(),
            "unique_items": priced["item_name"].nunique(),
            "average_price": markets["average_price"].mean(),
            "median_price": markets["average_price"].median(),
        })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records).sort_values("snapshot_timestamp").reset_index(
        drop=True
    )


def load_latest_market_snapshot() -> dict | None:
    """Return headline statistics from the newest processed snapshot."""

    snapshots = get_snapshots()
    if not snapshots:
        return None

    snapshot_file = snapshots[-1]
    dataframe, priced = load_data(snapshot_file)

    return {
        "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
        "source_file": str(snapshot_file),
        "priced_markets": _aggregate_snapshot(priced).shape[0],
        "unique_effects": priced["effect_name"].nunique(),
        "unique_items": priced["item_name"].nunique(),
    }


def load_unusual_catalog() -> pd.DataFrame:
    """Return searchable unusual markets from the latest processed snapshot."""

    snapshots = get_snapshots()
    if not snapshots:
        return pd.DataFrame()

    _, priced = load_data(snapshots[-1])
    required = ["effect_id", "effect_name", "defindex", "item_name"]
    if priced.empty or not set(required).issubset(priced.columns):
        return pd.DataFrame()

    return (
        priced[required]
        .drop_duplicates()
        .sort_values(["item_name", "effect_name"])
        .reset_index(drop=True)
    )


def load_unusual_trend(effect_id: int, defindex: int) -> pd.DataFrame:
    """Return the price history for one exact effect/item market."""

    records: list[dict] = []

    for snapshot_file in get_snapshots():
        dataframe, priced = load_data(snapshot_file)
        matching_rows = priced.loc[
            (priced["effect_id"] == effect_id)
            & (priced["defindex"] == defindex)
        ]

        if matching_rows.empty:
            records.append({"snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
                            "median_price": float("nan"), "average_price": float("nan"),
                            "low_price": float("nan"), "high_price": float("nan"),
                            "market_rows": 0, "source_updated_at": None})
            continue
        prepared = prepare_markets(matching_rows, "unusual")
        price = prepared["average_price"].iloc[0]

        records.append({
            "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
            "effect_name": matching_rows["effect_name"].iloc[0],
            "item_name": matching_rows["item_name"].iloc[0],
            "average_price": price,
            "median_price": price,
            "low_price": matching_rows[PRICE_COL].min(),
            "high_price": matching_rows[PRICE_COL].max(),
            "market_rows": len(matching_rows),
            "source_updated_at": prepared["source_updated_at"].iloc[0],
            "source_age_days": prepared["source_age_days"].iloc[0],
        })

    if not records:
        return pd.DataFrame()

    trend = pd.DataFrame(records).sort_values("snapshot_timestamp").reset_index(
        drop=True
    )
    trend["percent_change"] = trend["median_price"].pct_change(fill_method=None) * 100
    return trend


def compare_snapshots(old_snapshot, new_snapshot):
    """Outer coverage comparison; only matched usable prices have changes."""
    return compare_files(old_snapshot, new_snapshot)
