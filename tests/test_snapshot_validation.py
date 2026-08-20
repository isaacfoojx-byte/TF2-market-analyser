import csv
import tempfile
import unittest
from pathlib import Path

from scripts import validate_community_scrape_output as community_validation
from scripts import validate_scrape_output as unusual_validation


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def unusual_row(effect_id: int, defindex: int, price: float = 2.0) -> dict:
    return {
        "effect_id": effect_id,
        "effect_name": f"Effect {effect_id}",
        "item_name": f"Hat {defindex}",
        "bp_price_ref": 100,
        "scrape_timestamp": "2026-08-20T01:03:53",
        "defindex": defindex,
        "bp_price_keys_equivalent": price,
        "has_price": True,
        "item_type": "cosmetic",
    }


def community_row(item_name: str, price: float = 1.0) -> dict:
    return {
        "scrape_timestamp": "2026-08-20T01:58:28",
        "item_name": item_name,
        "item_type": "Cosmetic",
        "quality": "Unique",
        "craftable": True,
        "price_ref": price * 50,
        "key_price_ref": 50,
        "price_text": f"{price * 50:g} ref",
        "usd_price": 1.5,
        "stats_url": "https://backpack.tf/stats/Unique/Example",
        "source_url": "https://backpack.tf/spreadsheet",
        "price_keys_equivalent": price,
        "source_price_low": price * 50,
        "source_price_high": price * 50,
        "source_price_unit": "ref",
        "price_is_range": False,
        "display_price": price,
        "display_unit": "keys",
    }


class SnapshotValidationTests(unittest.TestCase):
    def test_accepts_a_valid_unusual_snapshot_pair(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            timestamp = "2026-08-20_01-03-53"
            rows = [unusual_row(1, 10), unusual_row(2, 11)]
            write_csv(output / "raw" / f"unusuals_{timestamp}.csv", rows)
            write_csv(output / "processed" / f"cleaned_{timestamp}.csv", rows)

            _, _, count = unusual_validation.validate_output(
                output,
                minimum_rows=1,
            )

            self.assertEqual(count, 2)

    def test_rejects_duplicate_unusual_markets(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            timestamp = "2026-08-20_01-03-53"
            rows = [unusual_row(1, 10), unusual_row(1, 10)]
            write_csv(output / "raw" / f"unusuals_{timestamp}.csv", rows)
            write_csv(output / "processed" / f"cleaned_{timestamp}.csv", rows)

            with self.assertRaisesRegex(ValueError, "duplicate unusual markets"):
                unusual_validation.validate_output(output, minimum_rows=1)

    def test_rejects_a_large_row_count_drop(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            previous = directory / "previous"
            current = directory / "cleaned_2026-08-20_01-03-53.csv"
            write_csv(
                previous / "cleaned_2026-08-19_01-03-40.csv",
                [{"value": index} for index in range(10)],
            )
            write_csv(current, [{"value": index} for index in range(7)])

            with self.assertRaisesRegex(ValueError, "fell 30.0%"):
                unusual_validation.validate_row_count(
                    current,
                    row_count=7,
                    previous_processed_dir=previous,
                    minimum_rows=1,
                    max_drop_fraction=0.20,
                )

    def test_accepts_a_valid_community_snapshot_pair(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            filename = "community_prices_2026-08-20_01-58-28.csv"
            processed_rows = [community_row("Hat A"), community_row("Hat B")]
            raw_rows = [
                {
                    key: value
                    for key, value in row.items()
                    if key in community_validation.REQUIRED_RAW_COLUMNS
                }
                for row in processed_rows
            ]
            write_csv(output / "raw" / filename, raw_rows)
            write_csv(output / "processed" / filename, processed_rows)

            _, _, raw_count, processed_count = community_validation.validate_output(
                output,
                minimum_rows=1,
            )

            self.assertEqual((raw_count, processed_count), (2, 2))

    def test_rejects_an_invalid_community_price(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            filename = "community_prices_2026-08-20_01-58-28.csv"
            processed_rows = [community_row("Hat A", price=0)]
            raw_rows = [
                {
                    key: value
                    for key, value in processed_rows[0].items()
                    if key in community_validation.REQUIRED_RAW_COLUMNS
                }
            ]
            write_csv(output / "raw" / filename, raw_rows)
            write_csv(output / "processed" / filename, processed_rows)

            with self.assertRaisesRegex(ValueError, "invalid processed prices"):
                community_validation.validate_output(output, minimum_rows=1)


if __name__ == "__main__":
    unittest.main()
