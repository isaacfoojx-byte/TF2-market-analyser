"""Clean timestamped backpack.tf community price-guide snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from processing.quality import market_id, parse_price, positive, write_cleaned


REQUIRED_COLUMNS = {
    "scrape_timestamp",
    "item_name",
    "item_type",
    "quality",
    "craftable",
    "price_ref",
    "key_price_ref",
    "price_text",
    "usd_price",
    "stats_url",
}

COLUMN_ORDER = [
    "scrape_timestamp",
    "source_url",
    "item_name",
    "item_type",
    "quality",
    "craftable",
    "price_ref",
    "key_price_ref",
    "price_keys_equivalent",
    "source_price_low",
    "source_price_high",
    "source_price_unit",
    "price_is_range",
    "display_price",
    "display_unit",
    "price_text",
    "usd_price",
    "stats_url",
]


def default_processed_path(raw_csv: str | Path) -> Path:
    """Put cleaned community data beside, not inside, the Unusual datasets."""

    raw_path = Path(raw_csv)
    if (
        raw_path.parent.name == "non_unusual"
        and raw_path.parent.parent.name == "raw"
    ):
        return (
            raw_path.parents[2]
            / "processed"
            / "non_unusual"
            / raw_path.name
        )
    return raw_path.parent.parent / "processed" / raw_path.name


def _normalise_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()


def _parse_displayed_price(value: object) -> pd.Series:
    low, high, unit = parse_price(value)
    return pd.Series({"source_price_low": low, "source_price_high": high,
                      "source_price_unit": unit or pd.NA})


def clean_community_prices(raw_csv, processed_csv=None, *,
                           previous_processed_dir=None, key_price_override=None,
                           change_threshold=0.5):
    """Preserve source files, quarantine unusable rows, and audit every decision."""
    raw_path = Path(raw_csv)
    original = pd.read_csv(raw_path)
    required = REQUIRED_COLUMNS - ({"key_price_ref"} if key_price_override is not None else set())
    missing = required - set(original.columns)
    if missing:
        raise ValueError(f"Community snapshot is missing required columns: {', '.join(sorted(missing))}")
    cleaned = original.copy()
    if key_price_override is not None:
        if not positive(key_price_override):
            raise ValueError("Key price must be positive and finite")
        cleaned["key_price_ref"] = float(key_price_override)
    cleaned["key_rate_source"] = "supplied_approximation" if key_price_override is not None else "captured"
    for column in ("item_name", "item_type", "quality", "price_text", "stats_url"):
        cleaned[column] = _normalise_text(cleaned[column]).replace("", pd.NA)
    timestamps = pd.to_datetime(cleaned["scrape_timestamp"], errors="coerce", format="mixed", utc=True)
    if timestamps.dropna().nunique() > 1:
        raise ValueError("Snapshot contains multiple collection timestamps")
    for column in ("price_ref", "key_price_ref", "usd_price"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned.loc[~cleaned["usd_price"].map(positive), "usd_price"] = float("nan")
    ranges = [parse_price(v) for v in cleaned["price_text"]]
    cleaned[["source_price_low", "source_price_high", "source_price_unit"]] = pd.DataFrame(
        ranges, index=cleaned.index, columns=["source_price_low", "source_price_high", "source_price_unit"],
    )
    cleaned["source_price_provenance"] = "captured_display"
    if {"source_value", "source_value_high", "source_currency"}.issubset(cleaned.columns):
        cleaned["source_price_low"] = pd.to_numeric(cleaned["source_value"], errors="coerce")
        cleaned["source_price_high"] = pd.to_numeric(cleaned["source_value_high"], errors="coerce")
        cleaned["source_price_unit"] = cleaned["source_currency"].replace({"metal": "ref"})
        cleaned["source_price_provenance"] = "api_original"
    reasons = {}
    for i, row in cleaned.iterrows():
        if not market_id(row, "community"):
            reasons[i] = "invalid_market_identity"
        elif pd.isna(timestamps[i]):
            reasons[i] = "invalid_collection_timestamp"
        elif not positive(row["key_price_ref"]):
            reasons[i] = "invalid_key_rate"
        elif (not positive(row["source_price_low"]) or not positive(row["source_price_high"])
              or row["source_price_high"] < row["source_price_low"]
              or row["source_price_unit"] not in {"keys", "ref"}):
            reasons[i] = "missing_or_invalid_source_price"
    cleaned = cleaned.drop(index=list(reasons)).copy()
    cleaned["craftable"] = cleaned["craftable"].astype(str).str.lower().isin({"true", "1", "1.0"})
    ids = cleaned.apply(lambda row: market_id(row, "community"), axis=1) if len(cleaned) else pd.Series(dtype=str)
    for _, group in cleaned.groupby(ids):
        if len(group) > 1:
            differing = len(group[["source_price_low", "source_price_high", "source_price_unit", "key_price_ref"]].drop_duplicates()) > 1
            for i in (group.index if differing else group.index[:-1]):
                reasons[i] = "conflicting_duplicate" if differing else "duplicate_observation"
    cleaned = cleaned.drop(index=[i for i in reasons if i in cleaned.index]).copy()
    midpoint = cleaned["source_price_low"] / 2 + cleaned["source_price_high"] / 2
    source_is_keys = cleaned["source_price_unit"].eq("keys")
    cleaned["price_ref"] = midpoint.where(~source_is_keys, midpoint * cleaned["key_price_ref"])
    cleaned["price_keys_equivalent"] = cleaned["price_ref"] / cleaned["key_price_ref"]
    invalid = ~cleaned["price_ref"].map(positive) | ~cleaned["price_keys_equivalent"].map(positive)
    reasons.update({i: "invalid_normalized_price" for i in cleaned.index[invalid]})
    cleaned = cleaned.loc[~invalid].copy()
    display_as_ref = cleaned["price_ref"] < cleaned["key_price_ref"]
    cleaned["display_unit"] = display_as_ref.map({True: "ref", False: "keys"})
    cleaned["display_price"] = cleaned["price_ref"].where(display_as_ref, cleaned["price_keys_equivalent"])
    cleaned["price_is_range"] = cleaned["source_price_low"] != cleaned["source_price_high"]
    # Preserve the legacy timestamp display while retaining explicit provenance.
    cleaned["scrape_timestamp"] = timestamps.loc[cleaned.index].dt.strftime("%Y-%m-%dT%H:%M:%S")
    if "source_url" not in cleaned:
        cleaned["source_url"] = pd.NA
    cleaned = cleaned.reindex(columns=COLUMN_ORDER + [c for c in cleaned if c not in COLUMN_ORDER])
    cleaned = cleaned.sort_values(["item_name", "quality", "craftable"], kind="stable")
    output = Path(processed_csv) if processed_csv else default_processed_path(raw_path)
    cleaned = write_cleaned(raw_path, original, cleaned, reasons, output, "community",
                            previous_processed_dir, change_threshold)
    return cleaned, output


def backfill_key_price(raw_csv, key_price_ref, processed_csv=None):
    """Use a documented approximate rate without changing the raw capture."""
    return clean_community_prices(raw_csv, processed_csv, key_price_override=key_price_ref)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean a raw backpack.tf community price spreadsheet snapshot.",
    )
    parser.add_argument("raw_csv", type=Path, help="Path to a raw community CSV")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the cleaned CSV",
    )
    parser.add_argument(
        "--key-price-ref",
        type=float,
        help="Use this approximate rate for cleaning; leave the raw snapshot unchanged.",
    )
    parser.add_argument("--previous-processed-dir", type=Path)
    parser.add_argument("--change-threshold", type=float, default=0.5)
    args = parser.parse_args()

    cleaned, output_path = clean_community_prices(
        args.raw_csv, args.output, key_price_override=args.key_price_ref,
        previous_processed_dir=args.previous_processed_dir,
        change_threshold=args.change_threshold,
    )
    print(f"Saved {len(cleaned):,} cleaned community price rows to {output_path}")


if __name__ == "__main__":
    main()
