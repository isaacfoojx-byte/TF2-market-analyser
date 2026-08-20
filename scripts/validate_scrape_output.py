from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path


REQUIRED_RAW_COLUMNS = {
    "effect_id",
    "effect_name",
    "item_name",
    "bp_price_ref",
    "scrape_timestamp",
}
REQUIRED_PROCESSED_COLUMNS = REQUIRED_RAW_COLUMNS | {
    "defindex",
    "bp_price_keys_equivalent",
    "has_price",
    "item_type",
}
MARKET_KEY = ("effect_id", "defindex")
MIN_PROCESSED_ROWS = 30_000
MAX_ROW_DROP_FRACTION = 0.20


def latest_csv(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matching {pattern} in {directory}")
    return matches[-1]


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = required_columns - columns
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


def validate_unique_markets(path: Path, rows: list[dict[str, str]]) -> None:
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for row in rows:
        key = tuple(row.get(column, "").strip() for column in MARKET_KEY)
        if not all(key):
            raise ValueError(f"{path} contains a blank unusual market key")
        if key in seen:
            duplicates += 1
        seen.add(key)

    if duplicates:
        raise ValueError(f"{path} contains {duplicates:,} duplicate unusual markets")


def validate_positive_prices(path: Path, rows: list[dict[str, str]]) -> None:
    invalid = 0
    for row in rows:
        try:
            price = float(row["bp_price_keys_equivalent"])
        except (KeyError, TypeError, ValueError):
            invalid += 1
            continue
        if price <= 0:
            invalid += 1

    if invalid:
        raise ValueError(f"{path} contains {invalid:,} invalid processed prices")


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

    previous_candidates = [
        path
        for path in sorted(previous_processed_dir.glob("cleaned_*.csv"))
        if path.name != processed_csv.name
    ]
    if not previous_candidates:
        return

    previous_csv = previous_candidates[-1]
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
) -> tuple[Path, Path, int]:
    raw_csv = latest_csv(output_dir / "raw", "unusuals_*.csv")
    filename_timestamp = raw_csv.stem.removeprefix("unusuals_")
    processed_csv = output_dir / "processed" / f"cleaned_{filename_timestamp}.csv"
    if not processed_csv.is_file():
        raise FileNotFoundError(
            "Missing processed CSV for the latest raw snapshot: "
            f"expected {processed_csv}"
        )

    raw_rows = read_csv(raw_csv, REQUIRED_RAW_COLUMNS)
    processed_rows = read_csv(processed_csv, REQUIRED_PROCESSED_COLUMNS)
    if len(raw_rows) != len(processed_rows):
        raise ValueError(
            f"Row-count mismatch: raw={len(raw_rows)}, processed={len(processed_rows)}"
        )

    validate_timestamp(raw_csv, raw_rows, filename_timestamp)
    validate_timestamp(processed_csv, processed_rows, filename_timestamp)
    validate_unique_markets(processed_csv, processed_rows)
    validate_positive_prices(processed_csv, processed_rows)
    validate_row_count(
        processed_csv,
        len(processed_rows),
        previous_processed_dir,
        minimum_rows,
        max_drop_fraction,
    )
    return raw_csv, processed_csv, len(processed_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one scraper output snapshot.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--previous-processed-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument("--minimum-rows", type=int, default=MIN_PROCESSED_ROWS)
    args = parser.parse_args()

    raw_csv, processed_csv, row_count = validate_output(
        args.output_dir,
        previous_processed_dir=args.previous_processed_dir,
        minimum_rows=args.minimum_rows,
    )
    print(f"Validated {row_count:,} unique, positively priced unusual markets")
    print(f"Raw CSV: {raw_csv}")
    print(f"Processed CSV: {processed_csv}")


if __name__ == "__main__":
    main()
