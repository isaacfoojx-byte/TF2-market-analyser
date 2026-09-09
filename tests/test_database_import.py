import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database.create_database import connect_database
from database.import_data import import_directory, import_snapshot
from database.queries import latest_markets, market_history
from processing.quality import market_id


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def unusual_row(timestamp="2026-09-09T01:00:00", price=2.0, item=10):
    return {
        "scrape_timestamp": timestamp,
        "defindex": item,
        "effect_id": 6,
        "item_name": f"Hat {item}",
        "effect_name": "Green Confetti",
        "bp_price_ref": price * 50,
        "bp_price_keys_equivalent": price,
        "key_price_ref": 50,
        "item_type": "cosmetic",
        "slot": "misc",
        "quality_flags": "source_update_unknown",
    }


def community_row(timestamp="2026-09-09T02:00:00", price=1.0):
    return {
        "scrape_timestamp": timestamp,
        "item_name": "Team Captain",
        "quality": "Unique",
        "craftable": True,
        "price_ref": price * 50,
        "price_keys_equivalent": price,
        "key_price_ref": 50,
        "source_price_low": price * 50,
        "source_price_high": price * 50,
        "source_price_unit": "ref",
        "price_is_range": False,
    }


class DatabaseImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.connection = connect_database(self.root / "test.db")
        self.addCleanup(self.connection.close)

    def test_schema_enables_foreign_keys_and_has_expected_version(self):
        self.assertEqual(
            self.connection.execute("PRAGMA foreign_keys").fetchone()[0], 1
        )
        self.assertEqual(
            self.connection.execute("PRAGMA user_version").fetchone()[0], 1
        )

    def test_import_is_idempotent_and_queryable(self):
        path = self.root / "cleaned_2026-09-09_01-00-00.csv"
        write_csv(path, [unusual_row()])

        first = import_snapshot(self.connection, path, "unusual")
        second = import_snapshot(self.connection, path, "unusual")

        self.assertEqual(first.action, "imported")
        self.assertEqual(second.action, "unchanged")
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0], 1
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM price_observations"
            ).fetchone()[0],
            1,
        )
        stable_id = market_id(unusual_row(), "unusual")
        self.assertEqual(market_history(self.connection, stable_id)[0]["price_keys"], 2)

    def test_identical_rerun_skips_csv_parsing(self):
        path = self.root / "cleaned_2026-09-09_01-00-00.csv"
        write_csv(path, [unusual_row()])
        import_snapshot(self.connection, path, "unusual")

        with patch(
            "database.import_data.read_snapshot",
            side_effect=AssertionError("an unchanged snapshot should be skipped"),
        ):
            result = import_snapshot(self.connection, path, "unusual")

        self.assertEqual(result.action, "unchanged")

    def test_unpriced_legacy_market_is_present_without_a_fake_price(self):
        path = self.root / "legacy.csv"
        priced = unusual_row()
        priced["has_price"] = True
        unpriced = unusual_row(item=11)
        unpriced.update(
            bp_price_ref="", bp_price_keys_equivalent="", has_price=False
        )
        write_csv(path, [priced, unpriced])

        result = import_snapshot(self.connection, path, "unusual")

        self.assertEqual(result.markets, 2)
        self.assertEqual(result.priced_observations, 1)
        statuses = self.connection.execute(
            "SELECT price_status, COUNT(*) FROM market_presence GROUP BY price_status"
        ).fetchall()
        self.assertEqual(
            {row["price_status"]: row[1] for row in statuses},
            {"priced": 1, "unpriced": 1},
        )

    def test_same_timestamp_with_changed_content_is_rejected(self):
        first = self.root / "first.csv"
        second = self.root / "second.csv"
        write_csv(first, [unusual_row(price=2)])
        write_csv(second, [unusual_row(price=3)])
        import_snapshot(self.connection, first, "unusual")

        with self.assertRaisesRegex(ValueError, "different unusual snapshot"):
            import_snapshot(self.connection, second, "unusual")

    def test_invalid_row_rolls_back_the_entire_snapshot(self):
        path = self.root / "bad.csv"
        rows = [unusual_row(), unusual_row(item=11)]
        rows[1]["bp_price_keys_equivalent"] = "infinity"
        write_csv(path, rows)

        with self.assertRaisesRegex(ValueError, r"bad.csv:3"):
            import_snapshot(self.connection, path, "unusual")

        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0], 0
        )
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM markets").fetchone()[0], 0
        )

    def test_duplicate_market_in_one_snapshot_is_rejected(self):
        path = self.root / "duplicate.csv"
        write_csv(path, [unusual_row(), unusual_row(price=3)])
        with self.assertRaisesRegex(ValueError, "Duplicate market identity"):
            import_snapshot(self.connection, path, "unusual")

    def test_market_metadata_updates_without_losing_first_seen(self):
        old = self.root / "old.csv"
        new = self.root / "new.csv"
        write_csv(old, [unusual_row(timestamp="2026-09-08T01:00:00")])
        renamed = unusual_row(timestamp="2026-09-09T01:00:00")
        renamed["item_name"] = "Renamed Hat"
        write_csv(new, [renamed])
        import_snapshot(self.connection, new, "unusual")
        import_snapshot(self.connection, old, "unusual")

        market = self.connection.execute(
            "SELECT item_name, first_seen_at, last_seen_at FROM markets"
        ).fetchone()
        self.assertEqual(market["item_name"], "Renamed Hat")
        self.assertEqual(market["first_seen_at"], "2026-09-08T01:00:00")
        self.assertEqual(market["last_seen_at"], "2026-09-09T01:00:00")

    def test_imports_both_datasets_from_processed_layout(self):
        write_csv(
            self.root / "cleaned_2026-09-09_01-00-00.csv", [unusual_row()]
        )
        write_csv(
            self.root / "non_unusual" / "community_prices_2026-09-09_02-00-00.csv",
            [community_row()],
        )

        results = import_directory(self.connection, self.root)

        self.assertEqual({result.dataset for result in results}, {"unusual", "community"})
        self.assertEqual(len(latest_markets(self.connection, "community")), 1)

    def test_quality_report_is_verified_and_issues_are_imported(self):
        path = self.root / "cleaned_2026-09-09_01-00-00.csv"
        write_csv(path, [unusual_row()])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        quality_path = self.root / "quality" / f"{path.stem}.quality.json"
        quality_path.parent.mkdir()
        quality_path.write_text(
            json.dumps(
                {
                    "cleaning_version": "2.0",
                    "processed_sha256": digest,
                    "accepted_rows": 1,
                    "warning_counts": {"source_update_unknown": 1},
                    "rejection_counts": {"duplicate_observation": 2},
                }
            ),
            encoding="utf-8",
        )

        result = import_snapshot(self.connection, path, "unusual")

        snapshot = self.connection.execute(
            "SELECT validation_status, cleaning_version FROM snapshots "
            "WHERE snapshot_id = ?",
            (result.snapshot_id,),
        ).fetchone()
        self.assertEqual(tuple(snapshot), ("validated", "2.0"))
        issues = self.connection.execute(
            "SELECT issue_code, issue_kind, affected_rows "
            "FROM snapshot_quality_issues ORDER BY issue_kind"
        ).fetchall()
        self.assertEqual(
            [tuple(issue) for issue in issues],
            [
                ("duplicate_observation", "rejection", 2),
                ("source_update_unknown", "warning", 1),
            ],
        )

    def test_quality_hash_mismatch_is_rejected_before_import(self):
        path = self.root / "cleaned_2026-09-09_01-00-00.csv"
        write_csv(path, [unusual_row()])
        quality_path = self.root / "quality" / f"{path.stem}.quality.json"
        quality_path.parent.mkdir()
        quality_path.write_text(
            json.dumps({"processed_sha256": "wrong", "accepted_rows": 1}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            import_snapshot(self.connection, path, "unusual")

    def test_stored_identity_must_match_derived_identity(self):
        path = self.root / "identity.csv"
        row = unusual_row()
        row["market_id"] = "tf2:unusual:wrong"
        write_csv(path, [row])
        with self.assertRaisesRegex(ValueError, "disagrees"):
            import_snapshot(self.connection, path, "unusual")

    def test_legacy_database_is_refused_without_modification(self):
        legacy = self.root / "legacy.db"
        import sqlite3

        connection = sqlite3.connect(legacy)
        connection.execute(
            "CREATE TABLE snapshots (snapshot_id INTEGER PRIMARY KEY, scraped_at TEXT)"
        )
        connection.commit()
        connection.close()

        with self.assertRaisesRegex(RuntimeError, "legacy database schema"):
            connect_database(legacy)

        connection = sqlite3.connect(legacy)
        columns = [
            row[1] for row in connection.execute("PRAGMA table_info(snapshots)")
        ]
        connection.close()
        self.assertEqual(columns, ["snapshot_id", "scraped_at"])


if __name__ == "__main__":
    unittest.main()
