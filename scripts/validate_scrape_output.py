from __future__ import annotations

import argparse
import csv
from pathlib import Path


REQUIRED_RAW_COLUMNS = {
    "effect_id",
    "effect_name",
    "item_name",
    "bp_price_ref",
    "scrape_timestamp",
}

REQUIRED_PROCESSED_COLUMNS = REQUIRED_RAW_COLUMNS | {
    "bp_price_keys_equivalent",
    "has_price",
    "item_type",
}


def latest_csv(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matching {pattern} in {directory}")
    return matches[-1]


def validate_csv(path: Path, required_columns: set[str]) -> int:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = required_columns - columns
        if missing:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(sorted(missing))}"
            )

        row_count = sum(1 for _ in reader)

    if row_count == 0:
        raise ValueError(f"{path} contains no data rows")

    return row_count


def validate_output(output_dir: Path) -> tuple[Path, Path, int]:
    raw_csv = latest_csv(output_dir / "raw", "unusuals_*.csv")
    timestamp = raw_csv.stem.removeprefix("unusuals_")
    processed_csv = output_dir / "processed" / f"cleaned_{timestamp}.csv"
    if not processed_csv.is_file():
        raise FileNotFoundError(
            "Missing processed CSV for the latest raw snapshot: "
            f"expected {processed_csv}"
        )

    raw_rows = validate_csv(raw_csv, REQUIRED_RAW_COLUMNS)
    processed_rows = validate_csv(processed_csv, REQUIRED_PROCESSED_COLUMNS)

    if raw_rows != processed_rows:
        raise ValueError(
            f"Row-count mismatch: raw={raw_rows}, processed={processed_rows}"
        )

    return raw_csv, processed_csv, processed_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one scraper output snapshot.")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    raw_csv, processed_csv, row_count = validate_output(args.output_dir)
    print(f"Validated {row_count:,} rows")
    print(f"Raw CSV: {raw_csv}")
    print(f"Processed CSV: {processed_csv}")


if __name__ == "__main__":
    main()
