"""Convert hosted PostgreSQL history to current prices plus price changes."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("postgres_schema.sql")
OBSERVATION_COLUMNS = (
    "snapshot_id", "market_id", "price_ref", "price_keys", "price_usd",
    "key_price_ref", "source_price_low", "source_price_high",
    "source_price_unit", "source_updated_at", "source_price_provenance",
    "key_rate_source", "price_is_range", "quality_flags", "raw_row_number",
)


def compact(database_url: str, *, prepare_only: bool = False) -> tuple[int, int, int]:
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError('Install PostgreSQL support with pip install "psycopg[binary]==3.3.5"') from error

    names = ",".join(OBSERVATION_COLUMNS)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        before = cursor.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0]
        cursor.execute(f"""
            INSERT INTO current_prices ({names})
            SELECT DISTINCT ON (o.market_id) {','.join(f'o.{name}' for name in OBSERVATION_COLUMNS)}
            FROM price_observations o JOIN snapshots s USING(snapshot_id)
            ORDER BY o.market_id,s.collected_at DESC,s.snapshot_id DESC
            ON CONFLICT(market_id) DO UPDATE SET
            {','.join(f'{name}=EXCLUDED.{name}' for name in OBSERVATION_COLUMNS if name != 'market_id')}
        """)
        current = cursor.execute("SELECT COUNT(*) FROM current_prices").fetchone()[0]
        if prepare_only:
            return before, before, current
        cursor.execute("DROP VIEW IF EXISTS market_presence")
        cursor.execute("""
            CREATE TABLE price_observations_compact
            (LIKE price_observations INCLUDING DEFAULTS INCLUDING CONSTRAINTS)
        """)
        cursor.execute(f"""
            WITH history AS (
                SELECT {','.join(f'o.{name}' for name in OBSERVATION_COLUMNS)},
                       LAG(o.price_ref) OVER w AS previous_ref,
                       LAG(o.price_keys) OVER w AS previous_keys,
                       ROW_NUMBER() OVER w AS sequence
                FROM price_observations o JOIN snapshots s USING(snapshot_id)
                WINDOW w AS (
                    PARTITION BY o.market_id ORDER BY s.collected_at,s.snapshot_id
                )
            )
            INSERT INTO price_observations_compact ({names})
            SELECT {names} FROM history
            WHERE sequence=1 OR price_ref IS DISTINCT FROM previous_ref
                             OR price_keys IS DISTINCT FROM previous_keys
        """)
        cursor.execute("ALTER TABLE price_observations_compact ADD PRIMARY KEY(snapshot_id,market_id)")
        cursor.execute("""
            ALTER TABLE price_observations_compact
            ADD FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
            ADD FOREIGN KEY(market_id) REFERENCES markets(market_id)
        """)
        cursor.execute("DROP TABLE price_observations")
        cursor.execute("ALTER TABLE price_observations_compact RENAME TO price_observations")
        cursor.execute(
            "CREATE INDEX idx_observations_market_snapshot "
            "ON price_observations(market_id,snapshot_id)"
        )
        cursor.execute("""
            CREATE VIEW market_presence AS
            SELECT snapshot_id,market_id,'priced'::TEXT AS price_status,
                   quality_flags,raw_row_number FROM price_observations
            UNION ALL
            SELECT snapshot_id,market_id,'unpriced'::TEXT AS price_status,
                   quality_flags,raw_row_number FROM unpriced_market_presence
        """)
        after = cursor.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0]
        if not current or after > before:
            raise RuntimeError(
                f"Compaction verification failed: before={before}, after={after}, current={current}"
            )
        cursor.execute("ANALYZE current_prices")
        cursor.execute("ANALYZE price_observations")
    return before, after, current


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", default="DATABASE_URL")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Create and populate current_prices without compacting history",
    )
    args = parser.parse_args()
    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        parser.error(f"{args.database_url_env} is not set")
    before, after, current = compact(database_url, prepare_only=args.prepare_only)
    if args.prepare_only:
        print(f"PostgreSQL current prices prepared: {current:,} rows.")
        return
    print(
        f"PostgreSQL history compacted: {before:,} -> {after:,} change rows; "
        f"{current:,} current prices."
    )


if __name__ == "__main__":
    main()
