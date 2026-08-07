import tempfile
import unittest
from pathlib import Path

import pandas as pd

from processing.community_prices import clean_community_prices


class CommunityPriceCleaningTests(unittest.TestCase):
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
            self.assertTrue(row["craftable"])
            self.assertEqual(row["scrape_timestamp"], "2026-08-07T12:00:00")


if __name__ == "__main__":
    unittest.main()
