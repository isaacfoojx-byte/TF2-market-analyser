"""Historical market summaries and comparisons built from processed snapshots."""

from pathlib import Path

import pandas as pd

from analytics.utils import PRICE_COL, get_snapshots, load_data


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
        timestamps = pd.to_datetime(dataframe["scrape_timestamp"], errors="coerce")
        if timestamps.notna().any():
            return timestamps.dropna().iloc[0]

    return pd.to_datetime(
        snapshot_file.stem.removeprefix("cleaned_"),
        format="%Y-%m-%d_%H-%M-%S",
    )


def _aggregate_snapshot(priced: pd.DataFrame) -> pd.DataFrame:
    """Aggregate individual rows into comparable effect/item markets."""

    return (
        priced
        .groupby(MARKET_KEYS)
        .agg(
            listings=("effect_id", "count"),
            average_price=(PRICE_COL, "mean"),
            median_price=(PRICE_COL, "median"),
        )
        .reset_index()
    )


def load_market_history() -> pd.DataFrame:
    """Return one aggregate row for every valid processed snapshot."""

    records: list[dict] = []

    for snapshot_file in get_snapshots():
        dataframe, priced = load_data(snapshot_file)

        if priced.empty:
            continue

        market_count = _aggregate_snapshot(priced).shape[0]
        records.append({
            "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
            "source_file": str(snapshot_file),
            "priced_markets": market_count,
            "priced_rows": len(priced),
            "unique_effects": priced["effect_name"].nunique(),
            "unique_items": priced["item_name"].nunique(),
            "average_price": priced[PRICE_COL].mean(),
            "median_price": priced[PRICE_COL].median(),
        })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records).sort_values("snapshot_timestamp").reset_index(
        drop=True
    )


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
            continue

        records.append({
            "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
            "effect_name": matching_rows["effect_name"].iloc[0],
            "item_name": matching_rows["item_name"].iloc[0],
            "average_price": matching_rows[PRICE_COL].mean(),
            "median_price": matching_rows[PRICE_COL].median(),
            "low_price": matching_rows[PRICE_COL].min(),
            "high_price": matching_rows[PRICE_COL].max(),
            "market_rows": len(matching_rows),
        })

    if not records:
        return pd.DataFrame()

    trend = pd.DataFrame(records).sort_values("snapshot_timestamp").reset_index(
        drop=True
    )
    trend["percent_change"] = trend["median_price"].pct_change() * 100
    return trend


def compare_snapshots(
    old_snapshot: str | Path,
    new_snapshot: str | Path,
) -> pd.DataFrame:
    """Compare two snapshots, retaining markets that have a price in both."""

    _, old_priced = load_data(Path(old_snapshot))
    _, new_priced = load_data(Path(new_snapshot))

    old_market = _aggregate_snapshot(old_priced)
    new_market = _aggregate_snapshot(new_priced)

    comparison = old_market.merge(
        new_market,
        on=MARKET_KEYS,
        how="inner",
        suffixes=("_old", "_new"),
    )

    if comparison.empty:
        return comparison

    comparison["price_change"] = (
        comparison["average_price_new"] - comparison["average_price_old"]
    )
    comparison["percent_change"] = (
        comparison["price_change"] / comparison["average_price_old"] * 100
    ).replace([float("inf"), float("-inf")], pd.NA)
    comparison["listing_change"] = (
        comparison["listings_new"] - comparison["listings_old"]
    )
    comparison["status"] = "Unchanged"
    comparison.loc[comparison["price_change"] > 0, "status"] = "Price Increased"
    comparison.loc[comparison["price_change"] < 0, "status"] = "Price Decreased"

    return comparison
