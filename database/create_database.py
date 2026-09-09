"""Create or upgrade the normalized TFAnalytics SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).with_name("market_v2.db")
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id INTEGER PRIMARY KEY,
    dataset TEXT NOT NULL CHECK (dataset IN ('unusual', 'community')),
    collected_at TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    cleaning_version TEXT,
    validation_status TEXT NOT NULL DEFAULT 'validated'
        CHECK (validation_status IN ('validated', 'legacy_unverified')),
    imported_at TEXT NOT NULL,
    market_count INTEGER NOT NULL CHECK (market_count >= 0),
    priced_observation_count INTEGER NOT NULL
        CHECK (priced_observation_count >= 0 AND priced_observation_count <= market_count),
    quality_report_json TEXT,
    UNIQUE (dataset, collected_at),
    UNIQUE (dataset, source_sha256)
);

CREATE TABLE IF NOT EXISTS markets (
    market_id INTEGER PRIMARY KEY,
    stable_id TEXT NOT NULL UNIQUE,
    dataset TEXT NOT NULL CHECK (dataset IN ('unusual', 'community')),
    defindex INTEGER,
    effect_id INTEGER,
    item_name TEXT NOT NULL,
    effect_name TEXT,
    quality TEXT,
    craftable INTEGER CHECK (craftable IN (0, 1) OR craftable IS NULL),
    tradable INTEGER NOT NULL DEFAULT 1 CHECK (tradable IN (0, 1)),
    item_type TEXT,
    slot TEXT,
    summary TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    CHECK (
        (dataset = 'unusual' AND defindex IS NOT NULL AND effect_id IS NOT NULL)
        OR
        (dataset = 'community' AND quality IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS price_observations (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    market_id INTEGER NOT NULL REFERENCES markets(market_id),
    price_ref REAL NOT NULL CHECK (price_ref > 0),
    price_keys REAL NOT NULL CHECK (price_keys > 0),
    price_usd REAL CHECK (price_usd >= 0),
    key_price_ref REAL CHECK (key_price_ref > 0),
    source_price_low REAL CHECK (source_price_low > 0),
    source_price_high REAL CHECK (source_price_high >= source_price_low),
    source_price_unit TEXT CHECK (
        source_price_unit IN ('ref', 'keys') OR source_price_unit IS NULL
    ),
    source_updated_at TEXT,
    source_price_provenance TEXT,
    key_rate_source TEXT,
    price_is_range INTEGER CHECK (price_is_range IN (0, 1) OR price_is_range IS NULL),
    quality_flags TEXT,
    raw_row_number INTEGER CHECK (raw_row_number >= 2 OR raw_row_number IS NULL),
    PRIMARY KEY (snapshot_id, market_id)
);

CREATE TABLE IF NOT EXISTS market_presence (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    market_id INTEGER NOT NULL REFERENCES markets(market_id),
    price_status TEXT NOT NULL CHECK (
        price_status IN ('priced', 'unpriced')
    ),
    quality_flags TEXT,
    raw_row_number INTEGER CHECK (raw_row_number >= 2 OR raw_row_number IS NULL),
    PRIMARY KEY (snapshot_id, market_id)
);

CREATE TABLE IF NOT EXISTS snapshot_quality_issues (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    issue_code TEXT NOT NULL,
    issue_kind TEXT NOT NULL CHECK (issue_kind IN ('warning', 'rejection')),
    affected_rows INTEGER NOT NULL CHECK (affected_rows >= 0),
    PRIMARY KEY (snapshot_id, issue_kind, issue_code)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_dataset_time
    ON snapshots(dataset, collected_at);
CREATE INDEX IF NOT EXISTS idx_markets_dataset_item
    ON markets(dataset, item_name);
CREATE INDEX IF NOT EXISTS idx_markets_unusual_identity
    ON markets(defindex, effect_id) WHERE dataset = 'unusual';
CREATE INDEX IF NOT EXISTS idx_observations_market_snapshot
    ON price_observations(market_id, snapshot_id);
CREATE INDEX IF NOT EXISTS idx_presence_market_snapshot
    ON market_presence(market_id, snapshot_id);

CREATE VIEW IF NOT EXISTS market_price_history AS
SELECT
    m.stable_id,
    m.dataset,
    m.item_name,
    m.effect_name,
    m.quality,
    m.craftable,
    s.collected_at,
    o.price_keys,
    o.price_ref,
    o.key_price_ref,
    o.source_updated_at,
    o.quality_flags,
    s.source_file
FROM price_observations AS o
JOIN snapshots AS s USING (snapshot_id)
JOIN markets AS m USING (market_id);
"""


def connect_database(path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a configured connection and ensure its schema exists."""

    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if current_version > SCHEMA_VERSION:
        connection.close()
        raise RuntimeError(
            f"Database schema {current_version} is newer than supported version "
            f"{SCHEMA_VERSION}."
        )
    existing_snapshot_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(snapshots)")
    }
    if existing_snapshot_columns and "dataset" not in existing_snapshot_columns:
        connection.close()
        raise RuntimeError(
            "This is the legacy database schema. Keep it as an archive and use "
            "market_v2.db (or another empty path) for normalized imports."
        )
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.executescript(SCHEMA)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()
    return connection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    with connect_database(args.database) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    print(f"Database ready: {args.database} (schema {version})")


if __name__ == "__main__":
    main()
