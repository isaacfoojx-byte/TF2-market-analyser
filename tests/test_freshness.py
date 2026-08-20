import unittest
from datetime import datetime, timedelta
from pathlib import Path

from analytics.community_history import BASE_DIR, COMMUNITY_DATA_DIR
from website.freshness import freshness_messages


class FreshnessTests(unittest.TestCase):
    def test_community_loader_uses_the_workflow_output_directory(self):
        self.assertEqual(
            COMMUNITY_DATA_DIR,
            BASE_DIR / "data" / "processed" / "non_unusual",
        )

    def test_fresh_snapshots_do_not_create_a_warning(self):
        messages = freshness_messages(
            now=datetime(2026, 8, 20, 12, 0, 0),
            unusual_snapshots=[Path("cleaned_2026-08-20_01-03-53.csv")],
            community_snapshots=[
                Path("community_prices_2026-08-20_01-58-28.csv")
            ],
        )

        self.assertEqual(messages, [])

    def test_stale_and_missing_snapshots_create_clear_warnings(self):
        messages = freshness_messages(
            now=datetime(2026, 8, 22, 12, 0, 0),
            unusual_snapshots=[Path("cleaned_2026-08-20_01-03-53.csv")],
            community_snapshots=[],
            maximum_age=timedelta(hours=36),
        )

        self.assertIn("Unusual market data may be stale", messages[0])
        self.assertEqual(messages[1], "Community price-guide data is unavailable.")


if __name__ == "__main__":
    unittest.main()
