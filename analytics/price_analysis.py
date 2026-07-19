import pandas as pd

df = pd.read_csv("data/processed/cleaned_unusuals.csv")

# Only items with known prices
priced = df[df["has_price"]]

#--------------------------------------
# Top 20 most expensive unusuals
#--------------------------------------
print("=" * 60)
print("Top 20 Most Expensive Unusuals")
print("=" * 60)

print(priced.nlargest(
    20,
    "price_ref"
)[[
    "effect_name",
    "item_name",
    "price_ref",
    "exist"
]])

#--------------------------------------
# Most expensive effects (by average price)
#--------------------------------------

print("=" * 60)
print("Highest Average-Priced Effects")
print("=" * 60)

effect_stats = (
    priced.groupby("effect_name")
      .agg(
          average_price=("price_ref", "mean"),
          count=("price_ref", "count")
      )
      .sort_values("average_price", ascending=False)
)

print(effect_stats.head(20).round(2))


#--------------------------------------
# Most expensive taunts
#--------------------------------------

print("=" * 60)
print("Top 20 Most Expensive Taunts")
print("=" * 60)

print(priced[priced["item_type"] == "taunt"].nlargest(
    20,
    "price_ref"
)[[
    "effect_name",
    "item_name",
    "price_ref",
    "exist"
]])


#--------------------------------------
# Average price by item type
#--------------------------------------

print("=" * 60)
print("Average price by item type:")
print("=" * 60)

print(
    priced.groupby("item_type")["price_ref"]
      .mean().round(2)
)


#--------------------------------------
# Median price by item type
#--------------------------------------

print("=" * 60)
print("Median Price by Item Type")
print("=" * 60)

print(
    priced.groupby("item_type")["price_ref"]
      .median()
      .round(2)
)

#--------------------------------------
# Maximum price by effect
#--------------------------------------

print("=" * 60)
print("Maximum Price by Effect")
print("=" * 60)

max_effect_price = (
    priced.groupby("effect_name")["price_ref"]
      .max()
      .sort_values(ascending=False)
      .head(20)
)

print(max_effect_price)

#--------------------------------------
# Items with Known Prices
#--------------------------------------

print("=" * 60)
print("Items with Known Prices")
print("=" * 60)

price_summary = (
    df.groupby("item_type")["has_price"]
      .agg(
          priced_items="sum",
          total_items="count"
      )
)

price_summary["unpriced_items"] = (
    price_summary["total_items"] - price_summary["priced_items"]
)

price_summary["priced_percentage"] = (
    price_summary["priced_items"] /
    price_summary["total_items"] * 100
).round(1)

print(price_summary)