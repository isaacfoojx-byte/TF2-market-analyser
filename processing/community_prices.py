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


def clean_community_prices(
    raw_csv: str | Path,
    processed_csv: str | Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Validate and clean a raw community price-guide snapshot.

    Rows without an item, quality, timestamp, or positive refined price cannot be
    compared meaningfully and are removed.  Duplicate item/quality/craftability
    rows from the same capture are collapsed deterministically.
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
    cleaned["usd_price"] = pd.to_numeric(cleaned["usd_price"], errors="coerce")
    cleaned.loc[cleaned["usd_price"] < 0, "usd_price"] = pd.NA

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
        subset=["scrape_timestamp", "item_name", "quality", "price_ref"],
    )
    cleaned = cleaned.loc[cleaned["price_ref"] > 0].copy()
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
    args = parser.parse_args()

    cleaned, output_path = clean_community_prices(args.raw_csv, args.output)
    print(f"Saved {len(cleaned):,} cleaned community price rows to {output_path}")


if __name__ == "__main__":
    main()
