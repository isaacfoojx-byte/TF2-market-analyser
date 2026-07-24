import sqlite3

conn = sqlite3.connect("market.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_at TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    effect_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    slot TEXT,
    item_type TEXT,
    defindex INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS market_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    price_ref REAL,
    exist INTEGER,
    summary TEXT,

    FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id),
    FOREIGN KEY(item_id) REFERENCES items(item_id)
)
""")

conn.commit()
conn.close()
