"""Copy a verified TFAnalytics SQLite database into an empty PostgreSQL database."""
from __future__ import annotations
import argparse
import os
import sqlite3
from pathlib import Path

from database.create_database import DEFAULT_DB_PATH

SCHEMA_PATH = Path(__file__).with_name("postgres_schema.sql")
TABLES = {
    "snapshots": ("snapshot_id", "dataset", "collected_at", "source_file", "source_sha256", "cleaning_version", "validation_status", "imported_at", "market_count", "priced_observation_count", "quality_report_json"),
    "markets": ("market_id", "stable_id", "dataset", "defindex", "effect_id", "item_name", "effect_name", "quality", "craftable", "tradable", "item_type", "slot", "summary", "first_seen_at", "last_seen_at"),
    "price_observations": ("snapshot_id", "market_id", "price_ref", "price_keys", "price_usd", "key_price_ref", "source_price_low", "source_price_high", "source_price_unit", "source_updated_at", "source_price_provenance", "key_rate_source", "price_is_range", "quality_flags", "raw_row_number"),
    "unpriced_market_presence": ("snapshot_id", "market_id", "quality_flags", "raw_row_number"),
    "snapshot_quality_issues": ("snapshot_id", "issue_code", "issue_kind", "affected_rows"),
}
BOOLEAN_COLUMNS = {"markets": {"craftable", "tradable"}, "price_observations": {"price_is_range"}}

def transformed(row: sqlite3.Row, table: str, columns: tuple[str, ...]) -> tuple:
    values = []
    for column in columns:
        value = row[column]
        if column in BOOLEAN_COLUMNS.get(table, set()) and value is not None:
            value = bool(value)
        values.append(value)
    return tuple(values)

def migrate(sqlite_path: Path, database_url: str) -> dict[str, int]:
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError('Install PostgreSQL support with pip install "psycopg[binary]==3.3.5"') from error
    if not sqlite_path.is_file():
        raise FileNotFoundError(sqlite_path)
    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    expected = {
        table: source.execute(
            "SELECT COUNT(*) FROM market_presence WHERE price_status='unpriced'"
            if table == "unpriced_market_presence"
            else f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        for table in TABLES
    }
    expected_presence = source.execute("SELECT COUNT(*) FROM market_presence").fetchone()[0]
    with psycopg.connect(database_url) as target:
        with target.cursor() as cursor:
            cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            occupied = {table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
            if any(occupied.values()):
                raise RuntimeError(f"Target PostgreSQL database is not empty: {occupied}")
            for table, columns in TABLES.items():
                names = ",".join(columns)
                rows = source.execute(
                    "SELECT snapshot_id,market_id,quality_flags,raw_row_number "
                    "FROM market_presence WHERE price_status='unpriced'"
                    if table == "unpriced_market_presence"
                    else f"SELECT {names} FROM {table}"
                )
                with cursor.copy(f"COPY {table} ({names}) FROM STDIN") as copy:
                    for row in rows:
                        copy.write_row(transformed(row, table, columns))
            observation_columns = TABLES["price_observations"]
            names = ",".join(observation_columns)
            cursor.execute(f"""
                INSERT INTO current_prices ({names})
                SELECT DISTINCT ON (o.market_id)
                       {','.join(f'o.{name}' for name in observation_columns)}
                FROM price_observations o JOIN snapshots s USING(snapshot_id)
                ORDER BY o.market_id,s.collected_at DESC,s.snapshot_id DESC
            """)
            for table, identity in (("snapshots", "snapshot_id"), ("markets", "market_id")):
                cursor.execute("SELECT setval(pg_get_serial_sequence(%s,%s), COALESCE(MAX(" + identity + "),1), MAX(" + identity + ") IS NOT NULL) FROM " + table, (table, identity))
            for table, count in expected.items():
                actual = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if actual != count:
                    raise RuntimeError(f"Verification failed for {table}: expected {count}, got {actual}")
            actual_presence = cursor.execute("SELECT COUNT(*) FROM market_presence").fetchone()[0]
            if actual_presence != expected_presence:
                raise RuntimeError(
                    "Verification failed for market_presence: "
                    f"expected {expected_presence}, got {actual_presence}"
                )
            cursor.execute("CREATE INDEX idx_snapshots_dataset_time ON snapshots(dataset,collected_at)")
            cursor.execute("CREATE INDEX idx_observations_market_snapshot ON price_observations(market_id,snapshot_id)")
            cursor.execute("ANALYZE")
    source.close()
    return expected

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--database-url-env", default="DATABASE_URL")
    args = parser.parse_args()
    url = os.environ.get(args.database_url_env)
    if not url:
        parser.error(f"{args.database_url_env} is not set")
    counts = migrate(args.sqlite, url)
    print("PostgreSQL migration verified: " + ", ".join(f"{name}={count:,}" for name, count in counts.items()))

if __name__ == "__main__":
    main()
