import sqlite3
import pandas as pd
from pathlib import Path

# ==========================================================
# STEP 1
# Connect to the SQLite database
# ==========================================================

conn = sqlite3.connect("database/market.db")
cursor = conn.cursor()

# ==========================================================
# STEP 2
# Find the newest processed CSV automatically
# ==========================================================

processed_folder = Path("data/processed")

csv_files = list(processed_folder.glob("cleaned_*.csv"))

if len(csv_files) == 0:
    raise FileNotFoundError("No processed CSV files found.")

# newest file based on modification time
latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)

print(f"Importing: {latest_csv.name}")

# ==========================================================
# STEP 3
# Read the CSV
# ==========================================================

df = pd.read_csv(latest_csv)

duplicates = df[df.duplicated(["effect_name", "item_name"], keep=False)]

print(f"Duplicate rows: {len(duplicates)}")

if not duplicates.empty:
    print(duplicates[["effect_name", "item_name"]])

duplicates = df[df["item_name"] == "Flame Thrower"]

print(duplicates.to_string())

# ==========================================================
# STEP 4
# Create a new snapshot
# Every import receives a unique snapshot ID
# ==========================================================

timestamp = df["scrape_timestamp"].iloc[0]

cursor.execute(
    """
    INSERT INTO snapshots(scraped_at)
    VALUES(?)
    """,
    (timestamp,)
)

snapshot_id = cursor.lastrowid

print(f"Snapshot ID: {snapshot_id}")

# ==========================================================
# STEP 5
# Insert new items into the items table
#
# We only store permanent information here.
#
# If the item already exists,
# SQLite ignores it because of INSERT OR IGNORE.
# ==========================================================

for _, row in df.iterrows():

    cursor.execute(
        """
        INSERT OR IGNORE INTO items
        (
            effect_id,
            effect_name,
            item_name,
            slot,
            item_type,
            summary,
            defindex
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["effect_id"],
            row["effect_name"],
            row["item_name"],
            row["slot"],
            row["item_type"],
            row["summary"],
            row["defindex"]
        )
    )

conn.commit()


# ==========================================================
# STEP 6
# Insert market history
#
# We first find the corresponding item_id.
# Then store today's market values.
# ==========================================================

for _, row in df.iterrows():

    cursor.execute(
        """
        SELECT item_id
        FROM items
        WHERE effect_id = ?
        AND defindex = ?
        """,
        (
            row["effect_id"],
            row["defindex"]
        )
    )

    result = cursor.fetchone()

    if result is None:
        continue

    item_id = result[0]

    cursor.execute(
        """
        INSERT INTO market_history
        (
            snapshot_id,
            item_id,
            bp_price_ref,
            bp_price_keys,
            bp_price_keys_equivalent,
            usd_price,
            key_low,
            key_high,
            key_mid,
            exist
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            item_id,
            row["bp_price_ref"],
            row["bp_price_keys"],
            row["bp_price_keys_equivalent"],
            row["usd_price"],
            row["key_low"],
            row["key_high"],
            row["key_mid"],
            row["exist"]
        )
)

# ==========================================================
# STEP 7
# Save everything
# ==========================================================

conn.commit()

# ==========================================================
# STEP 8
# Close the database
# ==========================================================

conn.close()

print("Import completed successfully.")