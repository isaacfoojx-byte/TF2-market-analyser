from utils import load_latest_data

df, priced = load_latest_data()

# --------------------------------------
# Build Effect Statistics Table
# --------------------------------------

effect_stats = (
    priced.groupby("effect_name")
          .agg(
              count=("bp_price_ref", "count"),
              average_price=("bp_price_ref", "mean"),
              median_price=("bp_price_ref", "median"),
              minimum_price=("bp_price_ref", "min"),
              maximum_price=("bp_price_ref", "max")
          )
)

effect_stats["price_range"] = (
    effect_stats["maximum_price"] -
    effect_stats["minimum_price"]
)

effect_stats = effect_stats.round(2)

print(effect_stats.columns)

# --------------------------------------
# Number of Unique Effects
# --------------------------------------

print("=" * 60)
print("Number of Unique Effects (with Priced Items)")
print("=" * 60)

print(f"Unique effects with priced items : {effect_stats.shape[0]}")

# --------------------------------------
# Most Common Effects
# --------------------------------------

print("=" * 60)
print("Top 20 Most Common Effects")
print("=" * 60)

print(
    effect_stats
        .sort_values("count", ascending=False)
        .head(20)
)

# --------------------------------------
# Highest Average-Priced Effects
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Average-Priced Effects")
print("=" * 60)

print(
    effect_stats
        .sort_values("average_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Highest Median-Priced Effects
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Median-Priced Effects")
print("=" * 60)

print(
    effect_stats
        .sort_values("median_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Highest Maximum-Priced Effects
# --------------------------------------

print("=" * 60)
print("Top 20 Highest Maximum-Priced Effects")
print("=" * 60)

print(
    effect_stats
        .sort_values("maximum_price", ascending=False)
        .head(20)
)

# --------------------------------------
# Widest Price Ranges
# --------------------------------------

print("=" * 60)
print("Top 20 Effects with Widest Price Ranges")
print("=" * 60)

print(
    effect_stats
        .sort_values("price_range", ascending=False)
        .head(20)
)
