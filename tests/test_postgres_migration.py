import sqlite3
import unittest

from database.migrate_to_postgres import SCHEMA_PATH, transformed


class PostgresMigrationTests(unittest.TestCase):
    def test_schema_contains_web_query_tables_and_indexes(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        for name in ("snapshots", "markets", "price_observations", "unpriced_market_presence"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {name}", schema)
        self.assertIn("CREATE OR REPLACE VIEW market_presence", schema)

    def test_sqlite_integer_flags_become_postgres_booleans(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE flags (craftable INTEGER, tradable INTEGER)")
        connection.execute("INSERT INTO flags VALUES (1, 0)")
        row = connection.execute("SELECT * FROM flags").fetchone()
        self.assertEqual(
            transformed(row, "markets", ("craftable", "tradable")),
            (True, False),
        )
        connection.close()


if __name__ == "__main__":
    unittest.main()
