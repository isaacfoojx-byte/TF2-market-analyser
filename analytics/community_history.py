"""Historical analytics for cleaned backpack.tf community price-guide snapshots."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
COMMUNITY_DATA_DIR = BASE_DIR / "data" / "community" / "processed"
MARKET_KEYS = ["item_name", "quality", "craftable"]
REQUIRED_COLUMNS = {
    "scrape_timestamp",
    "item_name",
    "item_type",
    "quality",
    "craftable",
    "price_ref",
    "key_price_ref",
    "price_keys_equivalent",
    "display_price",
    "display_unit",
    "source_price_low",
    "source_price_high",
    "source_price_unit",
    "price_is_range",
    "usd_price",
    "stats_url",
}
SNAPSHOT_PATTERN = re.compile(
    r"community_prices_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.csv"
)


def get_community_snapshots(snapshot_dir: str | Path | None = None) -> list[Path]:
    """Return cleaned community snapshots in chronological filename order."""

    directory = Path(snapshot_dir) if snapshot_dir else COMMUNITY_DATA_DIR
    if not directory.exists():
        return []

    return sorted(
        file
        for file in directory.glob("community_prices_*.csv")
        if SNAPSHOT_PATTERN.fullmatch(file.name)
    )


def community_history_signature() -> tuple[tuple[str, int, int], ...]:
    """Describe snapshots so Streamlit refreshes its cache after a new scrape."""

    return tuple(
        (snapshot.name, snapshot.stat().st_mtime_ns, snapshot.stat().st_size)
        for snapshot in get_community_snapshots()
    )


def _normalise_craftable(values: pd.Series) -> pd.Series:
    def convert(value: object) -> bool | object:
        if pd.isna(value):
            return pd.NA
        text = str(value).strip().lower()
        if text in {"true", "1", "1.0"}:
            return True
        if text in {"false", "0", "0.0"}:
            return False
        return pd.NA

    return values.map(convert).astype("boolean")


def _snapshot_timestamp(snapshot_file: Path, dataframe: pd.DataFrame) -> pd.Timestamp:
    timestamps = pd.to_datetime(dataframe["scrape_timestamp"], errors="coerce")
    if timestamps.notna().any():
        return timestamps.dropna().iloc[0]

    return pd.to_datetime(
        snapshot_file.stem.removeprefix("community_prices_"),
        format="%Y-%m-%d_%H-%M-%S",
    )


def _load_snapshot(snapshot_file: Path) -> pd.DataFrame:
    """Read a cleaned snapshot defensively so one bad file cannot break the UI."""

    dataframe = pd.read_csv(snapshot_file)
    missing = REQUIRED_COLUMNS.difference(dataframe.columns)
    if missing:
        return pd.DataFrame()

    dataframe = dataframe.copy()
    for column in ("item_name", "item_type", "quality", "stats_url"):
        dataframe[column] = dataframe[column].astype("string").str.strip()
    dataframe["price_ref"] = pd.to_numeric(dataframe["price_ref"], errors="coerce")
    dataframe["key_price_ref"] = pd.to_numeric(
        dataframe["key_price_ref"],
        errors="coerce",
    )
    dataframe["price_keys_equivalent"] = pd.to_numeric(
        dataframe["price_keys_equivalent"],
        errors="coerce",
    )
    dataframe["display_price"] = pd.to_numeric(
        dataframe["display_price"],
        errors="coerce",
    )
    dataframe["display_unit"] = dataframe["display_unit"].astype("string").str.strip()
    dataframe["source_price_low"] = pd.to_numeric(
        dataframe["source_price_low"],
        errors="coerce",
    )
    dataframe["source_price_high"] = pd.to_numeric(
        dataframe["source_price_high"],
        errors="coerce",
    )
    dataframe["source_price_unit"] = dataframe["source_price_unit"].astype(
        "string"
    ).str.strip()
    dataframe["price_is_range"] = dataframe["price_is_range"].map(
        lambda value: str(value).strip().lower() in {"true", "1", "1.0"}
    )
    dataframe["usd_price"] = pd.to_numeric(dataframe["usd_price"], errors="coerce")
    dataframe["craftable"] = _normalise_craftable(dataframe["craftable"])

    return dataframe.dropna(
        subset=["item_name", "quality", "price_ref", "key_price_ref", "price_keys_equivalent"]
    ).loc[
        lambda rows: (rows["price_ref"] > 0)
        & (rows["key_price_ref"] > 0)
        & (rows["price_keys_equivalent"] > 0)
    ].copy()


def _aggregate_snapshot(dataframe: pd.DataFrame) -> pd.DataFrame:
    return (
        dataframe.groupby(MARKET_KEYS, dropna=False)
        .agg(
            item_type=("item_type", "first"),
            guide_price_ref=("price_ref", "median"),
            guide_price_keys=("price_keys_equivalent", "median"),
            key_price_ref=("key_price_ref", "median"),
            guide_price_usd=("usd_price", "median"),
            display_price=("display_price", "median"),
            display_unit=("display_unit", "first"),
            source_price_low=("source_price_low", "first"),
            source_price_high=("source_price_high", "first"),
            source_price_unit=("source_price_unit", "first"),
            price_is_range=("price_is_range", "max"),
            stats_url=("stats_url", "first"),
            source_rows=("item_name", "size"),
        )
        .reset_index()
    )


def load_community_history(snapshot_dir: str | Path | None = None) -> pd.DataFrame:
    """Summarise price-guide coverage and values for every cleaned snapshot."""

    records: list[dict] = []
    for snapshot_file in get_community_snapshots(snapshot_dir):
        dataframe = _load_snapshot(snapshot_file)
        if dataframe.empty:
            continue

        markets = _aggregate_snapshot(dataframe)
        records.append({
            "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
            "source_file": str(snapshot_file),
            "priced_variants": len(markets),
            "unique_items": dataframe["item_name"].nunique(),
            "median_price_keys": dataframe["price_keys_equivalent"].median(),
            "average_price_keys": dataframe["price_keys_equivalent"].mean(),
            "key_price_ref": dataframe["key_price_ref"].median(),
        })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records).sort_values("snapshot_timestamp").reset_index(drop=True)


def load_community_catalog(snapshot_dir: str | Path | None = None) -> pd.DataFrame:
    """Return the latest searchable community item/quality/craftability catalog."""

    snapshots = get_community_snapshots(snapshot_dir)
    if not snapshots:
        return pd.DataFrame()

    dataframe = _load_snapshot(snapshots[-1])
    if dataframe.empty:
        return pd.DataFrame()

    return (
        _aggregate_snapshot(dataframe)
        .sort_values(["item_name", "quality", "craftable"], na_position="last")
        .reset_index(drop=True)
    )


def _craftable_mask(values: pd.Series, craftable: bool | None) -> pd.Series:
    if craftable is None:
        return values.isna()
    return values.eq(craftable).fillna(False)


def load_community_item_trend(
    item_name: str,
    quality: str,
    craftable: bool | None,
    snapshot_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Return guide-price history for one exact community item variant."""

    records: list[dict] = []
    for snapshot_file in get_community_snapshots(snapshot_dir):
        dataframe = _load_snapshot(snapshot_file)
        if dataframe.empty:
            continue

        matching_rows = dataframe.loc[
            dataframe["item_name"].eq(item_name)
            & dataframe["quality"].eq(quality)
            & _craftable_mask(dataframe["craftable"], craftable)
        ]
        if matching_rows.empty:
            continue

        records.append({
            "snapshot_timestamp": _snapshot_timestamp(snapshot_file, dataframe),
            "item_name": item_name,
            "quality": quality,
            "craftable": craftable,
            "median_price_keys": matching_rows["price_keys_equivalent"].median(),
            "low_price_keys": matching_rows["price_keys_equivalent"].min(),
            "high_price_keys": matching_rows["price_keys_equivalent"].max(),
            "key_price_ref": matching_rows["key_price_ref"].median(),
            "median_price_usd": matching_rows["usd_price"].median(),
            "display_price": matching_rows["display_price"].median(),
            "display_unit": matching_rows["display_unit"].dropna().iloc[0]
            if matching_rows["display_unit"].notna().any()
            else None,
            "source_price_low": matching_rows["source_price_low"].median(),
            "source_price_high": matching_rows["source_price_high"].median(),
            "source_price_unit": matching_rows["source_price_unit"].dropna().iloc[0]
            if matching_rows["source_price_unit"].notna().any()
            else None,
            "price_is_range": bool(matching_rows["price_is_range"].any()),
            "stats_url": matching_rows["stats_url"].dropna().iloc[0]
            if matching_rows["stats_url"].notna().any()
            else None,
            "source_rows": len(matching_rows),
        })

    if not records:
        return pd.DataFrame()

    trend = pd.DataFrame(records).sort_values("snapshot_timestamp").reset_index(
        drop=True
    )
    trend["percent_change"] = trend["median_price_keys"].pct_change() * 100
    return trend


def compare_community_snapshots(
    old_snapshot: str | Path,
    new_snapshot: str | Path,
) -> pd.DataFrame:
    """Compare guide-price variants shared by two snapshots."""

    old_data = _load_snapshot(Path(old_snapshot))
    new_data = _load_snapshot(Path(new_snapshot))
    if old_data.empty or new_data.empty:
        return pd.DataFrame()

    old_markets = _aggregate_snapshot(old_data)
    new_markets = _aggregate_snapshot(new_data)
    comparison = old_markets.merge(
        new_markets,
        on=MARKET_KEYS,
        how="inner",
        suffixes=("_old", "_new"),
    )
    if comparison.empty:
        return comparison

    comparison["price_change_keys"] = (
        comparison["guide_price_keys_new"] - comparison["guide_price_keys_old"]
    )
    comparison["percent_change"] = (
        comparison["price_change_keys"] / comparison["guide_price_keys_old"] * 100
    ).replace([float("inf"), float("-inf")], pd.NA)
    return comparison
