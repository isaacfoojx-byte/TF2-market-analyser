import sqlite3
import pandas as pd

df = pd.read_csv("data/processed/cleaned_2026-07-21_00-59-16.csv")

conn = sqlite3.connect("market.db")

df.to_sql(
    "items",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("Database created successfully.")