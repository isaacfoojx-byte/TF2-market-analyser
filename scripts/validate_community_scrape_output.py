"""Validate one raw and cleaned community price-guide snapshot pair."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REQUIRED_RAW_COLUMNS = {
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

REQUIRED_PROCESSED_COLUMNS = REQUIRED_RAW_COLUMNS | {
    "source_url",
    "price_keys_equivalent",
    "source_price_low",
    "source_price_high",
    "source_price_unit",
    "price_is_range",
    "display_price",
    "display_unit",
}


def latest_csv(directory: Path) -> Path:
    matches = sorted(directory.glob("community_prices_*.csv"))
    if not matches:
        raise FileNotFoundError(f"No community snapshots found in {directory}")
    return matches[-1]


def validate_csv(path: Path, required_columns: set[str]) -> int:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(sorted(missing))}"
            )
        row_count = sum(1 for _ in reader)

    if row_count == 0:
        raise ValueError(f"{path} contains no data rows")
    return row_count


def validate_output(output_dir: Path) -> tuple[Path, Path, int, int]:
    raw_csv = latest_csv(output_dir / "raw")
    processed_csv = output_dir / "processed" / raw_csv.name
    if not processed_csv.is_file():
        raise FileNotFoundError(
            "Missing processed CSV for the latest community snapshot: "
            f"expected {processed_csv}"
        )

    raw_rows = validate_csv(raw_csv, REQUIRED_RAW_COLUMNS)
    processed_rows = validate_csv(processed_csv, REQUIRED_PROCESSED_COLUMNS)
    if processed_rows > raw_rows:
        raise ValueError(
            "Processed community data has more rows than its raw snapshot: "
            f"raw={raw_rows}, processed={processed_rows}"
        )

    return raw_csv, processed_csv, raw_rows, processed_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate one community price-guide scraper output."
    )
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    raw_csv, processed_csv, raw_rows, processed_rows = validate_output(args.output_dir)
    print(f"Validated {raw_rows:,} raw rows and {processed_rows:,} processed rows")
    print(f"Raw CSV: {raw_csv}")
    print(f"Processed CSV: {processed_csv}")


if __name__ == "__main__":
    main()
