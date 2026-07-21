from utils import (
    load_latest_data,
    PRICE_COL,
    PRICE_UNIT
)

df, priced = load_latest_data()

# --------------------------------------
# Build Item Statistics Table
# --------------------------------------

item_stats = (
    priced.groupby("item_name")
          .agg(
              count=(PRICE_COL, "count"),
              average_price=(PRICE_COL, "mean"),
              median_price=(PRICE_COL, "median"),
              minimum_price=(PRICE_COL, "min"),
              maximum_price=(PRICE_COL, "max")
          )
)

item_stats["price_range"] = (
    item_stats["maximum_price"] -
    item_stats["minimum_price"]
)

item_stats = item_stats.round(2)

# --------------------------------------
# Highest Average-Priced Popular Items
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Average-Priced Items (100+ Variants)")
print("=" * 60)

popular_items = item_stats[item_stats["count"] >= 100]

print(
    popular_items
        .sort_values("average_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Number of Unique Items
# --------------------------------------

print("=" * 60)
print("Number of Unique Items")
print("=" * 60)

print(f"Unique items: {item_stats.shape[0]}")

# --------------------------------------
# Items with the Most Unusual Variants
# --------------------------------------

print("=" * 60)
print("Top 20 Items with the Most Unusual Variants")
print("=" * 60)

print(
    item_stats
        .sort_values("count", ascending=False)
        .head(20)
)

# --------------------------------------
# Highest Average-Priced Items
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Average-Priced Items")
print("=" * 60)

print(
    item_stats
        .sort_values("average_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Highest Median-Priced Items
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Median-Priced Items")
print("=" * 60)

print(
    item_stats
        .sort_values("median_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Highest Maximum-Priced Items
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Maximum-Priced Items")
print("=" * 60)

print(
    item_stats
        .sort_values("maximum_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Widest Price Ranges
# --------------------------------------

print("=" * 60)
print("Top 20 Items with the Widest Price Ranges")
print("=" * 60)

print(
    item_stats
        .sort_values("price_range", ascending=False)
        .head(20)
)

