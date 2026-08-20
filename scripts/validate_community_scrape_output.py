"""Validate one raw and cleaned community price-guide snapshot pair."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
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
MARKET_KEY = ("item_name", "quality", "craftable")
MIN_PROCESSED_ROWS = 4_000
MAX_ROW_DROP_FRACTION = 0.20


def latest_csv(directory: Path) -> Path:
    matches = sorted(directory.glob("community_prices_*.csv"))
    if not matches:
        raise FileNotFoundError(f"No community snapshots found in {directory}")
    return matches[-1]


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(sorted(missing))}"
            )
        rows = list(reader)

    if not rows:
        raise ValueError(f"{path} contains no data rows")
    return rows


def validate_timestamp(
    path: Path,
    rows: list[dict[str, str]],
    expected_filename_timestamp: str,
) -> None:
    timestamps = {
        row.get("scrape_timestamp", "").strip()
        for row in rows
        if row.get("scrape_timestamp", "").strip()
    }
    if len(timestamps) != 1:
        raise ValueError(f"{path} must contain exactly one scrape timestamp")

    timestamp = timestamps.pop()
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as error:
        raise ValueError(
            f"{path} contains an invalid scrape timestamp: {timestamp}"
        ) from error
    if parsed.strftime("%Y-%m-%d_%H-%M-%S") != expected_filename_timestamp:
        raise ValueError(
            f"{path} timestamp does not match its filename: {timestamp}"
        )


def validate_markets_and_prices(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    seen: set[tuple[str, str, str]] = set()
    duplicates = 0
    invalid_prices = 0

    for row in rows:
        key = tuple(row.get(column, "").strip().casefold() for column in MARKET_KEY)
        if not all(key):
            raise ValueError(f"{path} contains a blank community market key")
        if key in seen:
            duplicates += 1
        seen.add(key)

        try:
            prices = (
                float(row["price_ref"]),
                float(row["key_price_ref"]),
                float(row["price_keys_equivalent"]),
            )
        except (KeyError, TypeError, ValueError):
            invalid_prices += 1
            continue
        if any(price <= 0 for price in prices):
            invalid_prices += 1

    if duplicates:
        raise ValueError(f"{path} contains {duplicates:,} duplicate community markets")
    if invalid_prices:
        raise ValueError(f"{path} contains {invalid_prices:,} invalid processed prices")


def csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as file:
        return sum(1 for _ in csv.DictReader(file))


def validate_row_count(
    processed_csv: Path,
    row_count: int,
    previous_processed_dir: Path | None,
    minimum_rows: int,
    max_drop_fraction: float,
) -> None:
    if row_count < minimum_rows:
        raise ValueError(
            f"{processed_csv} contains only {row_count:,} rows; "
            f"minimum expected is {minimum_rows:,}"
        )

    if previous_processed_dir is None or not previous_processed_dir.exists():
        return

    candidates = [
        path
        for path in sorted(previous_processed_dir.glob("community_prices_*.csv"))
        if path.name != processed_csv.name
    ]
    if not candidates:
        return

    previous_csv = candidates[-1]
    previous_rows = csv_row_count(previous_csv)
    minimum_relative_rows = int(previous_rows * (1 - max_drop_fraction))
    if row_count < minimum_relative_rows:
        drop_percent = (1 - row_count / previous_rows) * 100
        raise ValueError(
            f"Processed row count fell {drop_percent:.1f}% versus "
            f"{previous_csv.name}: {previous_rows:,} -> {row_count:,}"
        )


def validate_output(
    output_dir: Path,
    previous_processed_dir: Path | None = None,
    minimum_rows: int = MIN_PROCESSED_ROWS,
    max_drop_fraction: float = MAX_ROW_DROP_FRACTION,
) -> tuple[Path, Path, int, int]:
    raw_csv = latest_csv(output_dir / "raw")
    processed_csv = output_dir / "processed" / raw_csv.name
    if not processed_csv.is_file():
        raise FileNotFoundError(
            "Missing processed CSV for the latest community snapshot: "
            f"expected {processed_csv}"
        )

    raw_rows = read_csv(raw_csv, REQUIRED_RAW_COLUMNS)
    processed_rows = read_csv(processed_csv, REQUIRED_PROCESSED_COLUMNS)
    if len(processed_rows) > len(raw_rows):
        raise ValueError(
            "Processed community data has more rows than its raw snapshot: "
            f"raw={len(raw_rows)}, processed={len(processed_rows)}"
        )

    filename_timestamp = raw_csv.stem.removeprefix("community_prices_")
    validate_timestamp(raw_csv, raw_rows, filename_timestamp)
    validate_timestamp(processed_csv, processed_rows, filename_timestamp)
    validate_markets_and_prices(processed_csv, processed_rows)
    validate_row_count(
        processed_csv,
        len(processed_rows),
        previous_processed_dir,
        minimum_rows,
        max_drop_fraction,
    )
    return raw_csv, processed_csv, len(raw_rows), len(processed_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate one community price-guide scraper output."
    )
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--previous-processed-dir",
        type=Path,
        default=Path("data/processed/non_unusual"),
    )
    parser.add_argument("--minimum-rows", type=int, default=MIN_PROCESSED_ROWS)
    args = parser.parse_args()

    raw_csv, processed_csv, raw_rows, processed_rows = validate_output(
        args.output_dir,
        previous_processed_dir=args.previous_processed_dir,
        minimum_rows=args.minimum_rows,
    )
    print(
        f"Validated {raw_rows:,} raw rows and {processed_rows:,} unique, "
        "positively priced community markets"
    )
    print(f"Raw CSV: {raw_csv}")
    print(f"Processed CSV: {processed_csv}")


if __name__ == "__main__":
    main()
