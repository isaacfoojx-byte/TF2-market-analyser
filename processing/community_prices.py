"""Clean timestamped backpack.tf community price-guide snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


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
    return raw_path.parent.parent / "processed" / raw_path.name


def _normalise_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()


def _parse_displayed_price(value: object) -> pd.Series:
    """Read a backpack.tf range and its unit without relying on its ref tooltip."""

    text = "" if pd.isna(value) else str(value).lower().replace(",", "")
    unit = "keys" if "key" in text else "ref" if "ref" in text else pd.NA
    values = pd.Series(text).str.extractall(r"(\d+(?:\.\d+)?)")[0].tolist()
    if unit is pd.NA or not values:
        return pd.Series({
            "source_price_low": pd.NA,
            "source_price_high": pd.NA,
            "source_price_unit": pd.NA,
        })

    low = float(values[0])
    high = float(values[1]) if len(values) > 1 else low
    return pd.Series({
        "source_price_low": min(low, high),
        "source_price_high": max(low, high),
        "source_price_unit": unit,
    })


def clean_community_prices(
    raw_csv: str | Path,
    processed_csv: str | Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Validate and clean a raw community price-guide snapshot.

    Rows without an item, quality, timestamp, positive refined price, or positive
    key price cannot be compared meaningfully and are removed. Duplicate
    item/quality/craftability rows from the same capture are collapsed
    deterministically.
    """

    raw_path = Path(raw_csv)
    frame = pd.read_csv(raw_path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Community snapshot is missing required columns: {missing_text}")

    cleaned = frame.copy()
    for column in ("item_name", "item_type", "quality", "price_text", "stats_url"):
        cleaned[column] = _normalise_text(cleaned[column]).replace("", pd.NA)

    cleaned["scrape_timestamp"] = pd.to_datetime(
        cleaned["scrape_timestamp"],
        errors="coerce",
    )
    cleaned["price_ref"] = pd.to_numeric(cleaned["price_ref"], errors="coerce")
    cleaned["key_price_ref"] = pd.to_numeric(
        cleaned["key_price_ref"],
        errors="coerce",
    )
    cleaned["usd_price"] = pd.to_numeric(cleaned["usd_price"], errors="coerce")
    cleaned.loc[cleaned["usd_price"] < 0, "usd_price"] = pd.NA
    cleaned[[
        "source_price_low",
        "source_price_high",
        "source_price_unit",
    ]] = cleaned["price_text"].apply(_parse_displayed_price)

    def normalise_craftable(value: object) -> bool | object:
        if pd.isna(value):
            return pd.NA
        text = str(value).strip().lower()
        if text in {"true", "1", "1.0"}:
            return True
        if text in {"false", "0", "0.0"}:
            return False
        return pd.NA

    cleaned["craftable"] = (
        cleaned["craftable"]
        .map(normalise_craftable)
        .astype("boolean")
    )

    cleaned = cleaned.dropna(
        subset=[
            "scrape_timestamp",
            "item_name",
            "quality",
            "key_price_ref",
            "source_price_low",
            "source_price_high",
            "source_price_unit",
        ],
    )
    cleaned = cleaned.loc[cleaned["key_price_ref"] > 0].copy()
    midpoint = (cleaned["source_price_low"] + cleaned["source_price_high"]) / 2
    source_is_keys = cleaned["source_price_unit"].eq("keys")
    cleaned["price_ref"] = midpoint.where(
        ~source_is_keys,
        midpoint * cleaned["key_price_ref"],
    )
    cleaned["price_keys_equivalent"] = cleaned["price_ref"] / cleaned["key_price_ref"]
    cleaned = cleaned.loc[
        (cleaned["price_ref"] > 0) & (cleaned["price_keys_equivalent"] > 0)
    ].copy()
    display_as_ref = cleaned["price_ref"] < cleaned["key_price_ref"]
    cleaned["display_unit"] = display_as_ref.map({True: "ref", False: "keys"})
    cleaned["display_price"] = cleaned["price_ref"].where(
        display_as_ref,
        cleaned["price_keys_equivalent"],
    )
    cleaned["price_is_range"] = (
        cleaned["source_price_low"] != cleaned["source_price_high"]
    )
    cleaned = cleaned.drop_duplicates(
        subset=["scrape_timestamp", "item_name", "quality", "craftable"],
        keep="last",
    )
    cleaned["scrape_timestamp"] = cleaned["scrape_timestamp"].dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )

    if "source_url" not in cleaned:
        cleaned["source_url"] = pd.NA
    cleaned = cleaned.reindex(columns=COLUMN_ORDER)
    cleaned = cleaned.sort_values(
        ["item_name", "quality", "craftable"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    output_path = Path(processed_csv) if processed_csv else default_processed_path(raw_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    return cleaned, output_path


def backfill_key_price(
    raw_csv: str | Path,
    key_price_ref: float,
    processed_csv: str | Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Add a supplied key rate to an older raw snapshot and clean it again.

    This is intended only for snapshots created before key conversion was added.
    The supplied rate should be documented as an approximation when it was not
    captured during the original scrape.
    """

    rate = float(key_price_ref)
    if rate <= 0:
        raise ValueError("Key price must be greater than zero.")

    raw_path = Path(raw_csv)
    frame = pd.read_csv(raw_path)
    if "price_ref" not in frame.columns:
        raise ValueError("Community snapshot has no refined-metal price column.")

    frame["key_price_ref"] = rate
    frame.to_csv(raw_path, index=False)
    return clean_community_prices(raw_path, processed_csv)


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
        help="Backfill this rate for an older raw snapshot before cleaning it.",
    )
    args = parser.parse_args()

    if args.key_price_ref is None:
        cleaned, output_path = clean_community_prices(args.raw_csv, args.output)
    else:
        cleaned, output_path = backfill_key_price(
            args.raw_csv,
            args.key_price_ref,
            args.output,
        )
    print(f"Saved {len(cleaned):,} cleaned community price rows to {output_path}")


if __name__ == "__main__":
    main()
