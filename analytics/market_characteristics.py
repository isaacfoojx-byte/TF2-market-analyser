from utils import (
    load_latest_data,
    PRICE_COL,
    PRICE_UNIT
)

df, priced = load_latest_data()

market_average = priced[PRICE_COL].mean()

# ---------------------------------------------------
# Effect Market Statistics
# ---------------------------------------------------

effect_market = (
    priced.groupby("effect_name")
          .agg(
              listings=(PRICE_COL, "count"),
              average_price=(PRICE_COL, "mean"),
              median_price=(PRICE_COL, "median"),
              std_dev=(PRICE_COL, "std"),
              min_price=(PRICE_COL, "min"),
              max_price=(PRICE_COL, "max")
          )
)

effect_market["premium"] = (
    effect_market["average_price"] - market_average
)

effect_market["coefficient_of_variation"] = (
    effect_market["std_dev"] /
    effect_market["average_price"]
)

effect_market["unique_items"] = (
    priced.groupby("effect_name")["item_name"].nunique()
)

effect_market = effect_market.round(2)

# ---------------------------------------------------
# Item Market Statistics
# ---------------------------------------------------

item_market = (
    priced.groupby("item_name")
          .agg(
              listings=(PRICE_COL, "count"),
              average_price=(PRICE_COL, "mean"),
              median_price=(PRICE_COL, "median"),
              std_dev=(PRICE_COL, "std"),
              min_price=(PRICE_COL, "min"),
              max_price=(PRICE_COL, "max")
          )
)

item_market["premium"] = (
    item_market["average_price"] - market_average
)

item_market["coefficient_of_variation"] = (
    item_market["std_dev"] /
    item_market["average_price"]
)

item_market["unique_effects"] = (
    priced.groupby("item_name")["effect_name"].nunique()
)

item_market = item_market.round(2)

# ---------------------------------------------------
# Overall Market Statistics
# ---------------------------------------------------

print("=" * 60)
print("Overall Market")
print("=" * 60)

print(f"Average unusual price : {market_average:,.2f} {PRICE_UNIT}")
print(f"Median unusual price  : {priced[PRICE_COL].median():,.2f} {PRICE_UNIT}")
print(f"Number of listings    : {len(priced):,}")

# ---------------------------------------------------
# Highest Premium Effects
# ---------------------------------------------------

print("=" * 60)
print("Highest Premium Effects")
print("=" * 60)

print(
    effect_market
        .sort_values("premium", ascending=False)
        .head(20)
)

# ---------------------------------------------------
# Most Stable Effects
# ---------------------------------------------------

print("=" * 60)
print("Most Stable Effects")
print("=" * 60)

stable_effects = effect_market[
    effect_market["listings"] >= 50
]

print(
    stable_effects
        .sort_values("coefficient_of_variation")
        .head(20)
)

# ---------------------------------------------------
# Most Volatile Effects
# ---------------------------------------------------

print("=" * 60)
print("Most Volatile Effects")
print("=" * 60)

print(
    stable_effects
        .sort_values("coefficient_of_variation",
                     ascending=False)
        .head(20)
)

# ---------------------------------------------------
# Highest Premium Items
# ---------------------------------------------------

print("=" * 60)
print("Highest Premium Items")
print("=" * 60)

print(
    item_market
        .sort_values("premium", ascending=False)
        .head(20)
)

# ---------------------------------------------------
# Most Stable Items
# ---------------------------------------------------

print("=" * 60)
print("Most Stable Items")
print("=" * 60)

stable_items = item_market[
    item_market["listings"] >= 50
]

print(
    stable_items
        .sort_values("coefficient_of_variation")
        .head(20)
)

# ---------------------------------------------------
# Most Volatile Items
# ---------------------------------------------------

print("=" * 60)
print("Most Volatile Items")
print("=" * 60)

print(
    stable_items
        .sort_values("coefficient_of_variation",
                     ascending=False)
        .head(20)
)

# ---------------------------------------------------
# Cosmetics with the Most Different Effects
# ---------------------------------------------------

print("=" * 60)
print("Items with the Most Unique Effects")
print("=" * 60)

print(
    item_market
        .sort_values("unique_effects",
                     ascending=False)
        .head(20)
)

# ---------------------------------------------------
# Effects Used on the Most Cosmetics
# ---------------------------------------------------

print("=" * 60)
print("Effects Found on the Most Items")
print("=" * 60)

print(
    effect_market
        .sort_values("unique_items",
                     ascending=False)
        .head(20)
)

