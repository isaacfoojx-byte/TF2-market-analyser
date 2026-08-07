import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from analytics.community_history import (
    compare_community_snapshots,
    load_community_catalog,
    load_community_history,
    load_community_item_trend,
)


def write_snapshot(directory: Path, timestamp: str, price_ref: float) -> Path:
    path = directory / f"community_prices_{timestamp}.csv"
    pd.DataFrame([
        {
            "scrape_timestamp": datetime.strptime(
                timestamp, "%Y-%m-%d_%H-%M-%S"
            ).isoformat(timespec="seconds"),
            "source_url": "https://backpack.tf/spreadsheet",
            "item_name": "Team Captain",
            "item_type": "Cosmetic",
            "quality": "Unique",
            "craftable": True,
            "price_ref": price_ref,
            "price_text": f"{price_ref} ref",
            "usd_price": 1.5,
            "stats_url": "https://backpack.tf/stats/Unique/Team%20Captain",
        },
        {
            "scrape_timestamp": datetime.strptime(
                timestamp, "%Y-%m-%d_%H-%M-%S"
            ).isoformat(timespec="seconds"),
            "source_url": "https://backpack.tf/spreadsheet",
            "item_name": "Back Scratcher",
            "item_type": "Weapon",
            "quality": "Unique",
            "craftable": False,
            "price_ref": 2,
            "price_text": "2 ref",
            "usd_price": 0.1,
            "stats_url": "https://backpack.tf/stats/Unique/Back%20Scratcher",
        },
    ]).to_csv(path, index=False)
    return path


class CommunityHistoryTests(unittest.TestCase):
    def test_catalog_history_trend_and_comparison(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            old_snapshot = write_snapshot(directory, "2026-08-01_12-00-00", 50)
            new_snapshot = write_snapshot(directory, "2026-08-02_12-00-00", 55)

            history = load_community_history(directory)
            catalog = load_community_catalog(directory)
            trend = load_community_item_trend(
                "Team Captain", "Unique", True, directory
            )
            comparison = compare_community_snapshots(old_snapshot, new_snapshot)

        self.assertEqual(len(history), 2)
        self.assertEqual(len(catalog), 2)
        self.assertEqual(len(trend), 2)
        self.assertEqual(trend.iloc[-1]["median_price_ref"], 55)
        self.assertAlmostEqual(trend.iloc[-1]["percent_change"], 10)
        team_captain = comparison.loc[
            comparison["item_name"].eq("Team Captain")
        ].iloc[0]
        self.assertEqual(team_captain["price_change_ref"], 5)
        self.assertAlmostEqual(team_captain["percent_change"], 10)


if __name__ == "__main__":
    unittest.main()
