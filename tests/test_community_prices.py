import tempfile
import unittest
from pathlib import Path

import pandas as pd

from processing.community_prices import (
    backfill_key_price,
    clean_community_prices,
    default_processed_path,
)


class CommunityPriceCleaningTests(unittest.TestCase):
    def test_routes_non_unusual_archives_to_the_processed_folder(self):
        raw_path = Path("data/raw/non_unusual/community_prices_test.csv")

        self.assertEqual(
            default_processed_path(raw_path),
            Path("data/processed/non_unusual/community_prices_test.csv"),
        )

    def test_removes_invalid_rows_and_normalises_a_snapshot(self):
        rows = pd.DataFrame(
            [
                {
                    "scrape_timestamp": "2026-08-07 12:00:00",
                    "source_url": "https://backpack.tf/spreadsheet",
                    "item_name": "  Team   Captain ",
                    "item_type": " Cosmetic ",
                    "quality": " Unique ",
                    "craftable": "1",
                    "price_ref": "50.5",
                    "key_price_ref": "50",
                    "price_text": "50-51 ref",
                    "usd_price": "1.54",
                    "stats_url": "https://backpack.tf/stats/Unique/Team%20Captain",
                },
                {
                    "scrape_timestamp": "2026-08-07 12:00:00",
                    "source_url": "https://backpack.tf/spreadsheet",
                    "item_name": "Team Captain",
                    "item_type": "Cosmetic",
                    "quality": "Unique",
                    "craftable": "true",
                    "price_ref": 51,
                    "key_price_ref": 50,
                    "price_text": "51 ref",
                    "usd_price": 1.55,
                    "stats_url": "https://backpack.tf/stats/Unique/Team%20Captain",
                },
                {
                    "scrape_timestamp": "2026-08-07 12:00:00",
                    "source_url": "https://backpack.tf/spreadsheet",
                    "item_name": "No price",
                    "item_type": "Cosmetic",
                    "quality": "Unique",
                    "craftable": False,
                    "price_ref": 0,
                    "key_price_ref": 50,
                    "price_text": "",
                    "usd_price": None,
                    "stats_url": None,
                },
            ]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_path = Path(temporary_directory) / "community_prices_test.csv"
            rows.to_csv(raw_path, index=False)
            cleaned, output_path = clean_community_prices(raw_path)
            self.assertEqual(len(cleaned), 1)
            self.assertTrue(output_path.exists())
            row = cleaned.iloc[0]
            self.assertEqual(row["item_name"], "Team Captain")
            self.assertEqual(row["quality"], "Unique")
            self.assertEqual(row["price_ref"], 51)
            self.assertEqual(row["key_price_ref"], 50)
            self.assertEqual(row["price_keys_equivalent"], 1.02)
            self.assertEqual(row["display_price"], 1.02)
            self.assertEqual(row["display_unit"], "keys")
            self.assertFalse(row["price_is_range"])
            self.assertTrue(row["craftable"])
            self.assertEqual(row["scrape_timestamp"], "2026-08-07T12:00:00")

    def test_backfill_adds_a_key_rate_to_an_older_raw_snapshot(self):
        rows = pd.DataFrame([
            {
                "scrape_timestamp": "2026-08-07T12:00:00",
                "source_url": "https://backpack.tf/spreadsheet",
                "item_name": "Team Captain",
                "item_type": "Cosmetic",
                "quality": "Unique",
                "craftable": True,
                "price_ref": 50,
                "price_text": "50 ref",
                "usd_price": 1.5,
                "stats_url": "https://backpack.tf/stats/Unique/Team%20Captain",
            },
        ])

        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_path = Path(temporary_directory) / "community_prices_test.csv"
            rows.to_csv(raw_path, index=False)
            cleaned, output_path = backfill_key_price(raw_path, key_price_ref=50)

            self.assertTrue(output_path.exists())
            self.assertEqual(cleaned.iloc[0]["price_keys_equivalent"], 1)
            raw_data = pd.read_csv(raw_path)
            self.assertEqual(raw_data.iloc[0]["key_price_ref"], 50)

    def test_uses_range_midpoints_and_backpack_style_display_units(self):
        rows = pd.DataFrame([
            {
                "scrape_timestamp": "2026-08-07T12:00:00",
                "source_url": "https://backpack.tf/spreadsheet",
                "item_name": "Key Range",
                "item_type": "Cosmetic",
                "quality": "Unique",
                "craftable": True,
                "price_ref": 0,
                "key_price_ref": 64.495,
                "price_text": "16-19 keys",
                "usd_price": None,
                "stats_url": None,
            },
            {
                "scrape_timestamp": "2026-08-07T12:00:00",
                "source_url": "https://backpack.tf/spreadsheet",
                "item_name": "Ref Range",
                "item_type": "Cosmetic",
                "quality": "Unique",
                "craftable": True,
                "price_ref": 0,
                "key_price_ref": 64.495,
                "price_text": "5-8.55 ref",
                "usd_price": None,
                "stats_url": None,
            },
            {
                "scrape_timestamp": "2026-08-07T12:00:00",
                "source_url": "https://backpack.tf/spreadsheet",
                "item_name": "Barter Item",
                "item_type": "Cosmetic",
                "quality": "Unique",
                "craftable": True,
                "price_ref": 1.39,
                "key_price_ref": 64.495,
                "price_text": "1 hat",
                "usd_price": None,
                "stats_url": None,
            },
        ])

        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_path = Path(temporary_directory) / "community_prices_test.csv"
            rows.to_csv(raw_path, index=False)
            cleaned, _ = clean_community_prices(raw_path)

        self.assertEqual(len(cleaned), 2)
        key_row = cleaned.loc[cleaned["item_name"].eq("Key Range")].iloc[0]
        ref_row = cleaned.loc[cleaned["item_name"].eq("Ref Range")].iloc[0]
        self.assertEqual(key_row["price_keys_equivalent"], 17.5)
        self.assertEqual(key_row["display_unit"], "keys")
        self.assertTrue(key_row["price_is_range"])
        self.assertAlmostEqual(ref_row["price_ref"], 6.775)
        self.assertEqual(ref_row["display_unit"], "ref")
        self.assertTrue(ref_row["price_is_range"])


if __name__ == "__main__":
    unittest.main()
