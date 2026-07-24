import sqlite3
from pathlib import Path

# ==========================================================
# Connect to (or create) the database
# ==========================================================

DB_PATH = Path(__file__).parent / "market.db"
conn = sqlite3.connect(DB_PATH)

conn.execute("PRAGMA foreign_keys = ON")

cursor = conn.cursor()

# ==========================================================
# Snapshots
#
# Each scrape creates ONE snapshot.
# Every market record belongs to one snapshot.
# ==========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS snapshots (

    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,

    scraped_at TEXT NOT NULL
)
""")

# ==========================================================
# Items
#
# Information that never (or almost never) changes.
# One row per unusual item.
# ==========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (

    item_id INTEGER PRIMARY KEY AUTOINCREMENT,

    effect_id INTEGER,

    effect_name TEXT NOT NULL,

    item_name TEXT NOT NULL,

    slot TEXT,

    item_type TEXT,

    summary TEXT,

    defindex INTEGER,

    UNIQUE(effect_id, defindex)
)
""")

# ==========================================================
# Market History
#
# Information that changes every scrape.
# This is where the historical data lives.
# ==========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS market_history (

    history_id INTEGER PRIMARY KEY AUTOINCREMENT,

    snapshot_id INTEGER NOT NULL,

    item_id INTEGER NOT NULL,

    bp_price_ref REAL,

    bp_price_keys REAL,

    bp_price_keys_equivalent REAL,

    usd_price REAL,

    key_low REAL,

    key_high REAL,

    key_mid REAL,

    exist INTEGER,

    UNIQUE(snapshot_id, item_id),

    FOREIGN KEY(snapshot_id)
        REFERENCES snapshots(snapshot_id),

    FOREIGN KEY(item_id)
        REFERENCES items(item_id)
)
""")

# ==========================================================
# Optional indexes
#
# These dramatically speed up searches once your database
# grows to hundreds of thousands of historical records.
# ==========================================================

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_market_item
ON market_history(item_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_market_snapshot
ON market_history(snapshot_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_item_lookup
ON items(effect_name, item_name);
""")

# ==========================================================
# Save changes
# ==========================================================

conn.commit()

print("Database successfully created.")

conn.close()
