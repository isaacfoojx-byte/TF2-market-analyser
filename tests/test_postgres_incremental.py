import tempfile
import unittest
from pathlib import Path

from database.import_postgres import (
    _boolean_market,
    _boolean_observation,
    prepare_snapshot,
)
from tests.test_database_import import unusual_row, write_csv


class PostgresIncrementalTests(unittest.TestCase):
    def test_prepares_priced_and_unpriced_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.csv"
            priced = unusual_row()
            priced["has_price"] = True
            priced["price_is_range"] = "true"
            unpriced = unusual_row(item=11)
            unpriced.update(has_price=False, bp_price_ref="", bp_price_keys_equivalent="")
            write_csv(path, [priced, unpriced])

            prepared, collected_at, report, status = prepare_snapshot(path, "unusual")

        self.assertEqual(len(prepared), 2)
        self.assertIsNotNone(prepared[0][2])
        self.assertIsNone(prepared[1][2])
        self.assertEqual(collected_at, "2026-09-09T01:00:00")
        self.assertIsNone(report)
        self.assertEqual(status, "legacy_unverified")

    def test_converts_sqlite_style_flags_for_postgres(self):
        market = ("id", "unusual", 1, 2, "Hat", "Effect", None, 1, None, None, None, "old", "new")
        observation = (1.0, 2.0, None, None, None, None, None, None, None, None, 0, None, None)
        self.assertIs(_boolean_market(market)[7], True)
        self.assertIs(_boolean_observation(observation)[10], False)


if __name__ == "__main__":
    unittest.main()
