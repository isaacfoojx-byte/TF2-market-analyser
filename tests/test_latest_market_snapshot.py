import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from analytics import history
from website import utils as website_utils


class LatestMarketSnapshotTests(unittest.TestCase):
    def test_uses_newest_processed_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            older = directory / "cleaned_2026-08-19_01-03-40.csv"
            newest = directory / "cleaned_2026-08-20_01-03-53.csv"

            rows = pd.DataFrame(
                [
                    {
                        "effect_id": 1,
                        "effect_name": "Effect A",
                        "defindex": 10,
                        "item_name": "Hat A",
                        "bp_price_keys_equivalent": 2.0,
                        "has_price": True,
                        "scrape_timestamp": "2026-08-20T01:03:53",
                    },
                    {
                        "effect_id": 2,
                        "effect_name": "Effect B",
                        "defindex": 10,
                        "item_name": "Hat A",
                        "bp_price_keys_equivalent": 3.0,
                        "has_price": True,
                        "scrape_timestamp": "2026-08-20T01:03:53",
                    },
                ]
            )
            rows.iloc[:1].to_csv(older, index=False)
            rows.to_csv(newest, index=False)

            with patch.object(history, "get_snapshots", return_value=[older, newest]):
                snapshot = history.load_latest_market_snapshot()

            self.assertIsNotNone(snapshot)
            self.assertEqual(
                snapshot["snapshot_timestamp"],
                pd.Timestamp("2026-08-20T01:03:53"),
            )
            self.assertEqual(snapshot["priced_markets"], 2)
            self.assertEqual(snapshot["unique_effects"], 2)
            self.assertEqual(snapshot["unique_items"], 1)

    def test_cached_snapshot_refreshes_when_file_signature_changes(self):
        old_signature = (("old.csv", 1, 10),)
        new_signature = (
            ("old.csv", 1, 10),
            ("new.csv", 2, 20),
        )
        old_snapshot = {"snapshot_timestamp": "2026-08-19T01:03:40"}
        new_snapshot = {"snapshot_timestamp": "2026-08-20T01:03:53"}

        website_utils._load_latest_unusual_snapshot.clear()
        with patch.object(
            website_utils,
            "load_latest_market_snapshot",
            side_effect=[old_snapshot, new_snapshot],
        ):
            self.assertEqual(
                website_utils._load_latest_unusual_snapshot(old_signature),
                old_snapshot,
            )
            self.assertEqual(
                website_utils._load_latest_unusual_snapshot(new_signature),
                new_snapshot,
            )
        website_utils._load_latest_unusual_snapshot.clear()


if __name__ == "__main__":
    unittest.main()
