import pandas as pd

df = pd.read_csv("data/cleaned_unusuals.csv")

#--------------------------------------
# Top 20 most expensive unusuals
#--------------------------------------
print("=" * 60)
print("Top 20 Most Expensive Unusuals")
print("=" * 60)

print(df.nlargest(
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

avg_effect_price = (
    df.groupby("effect_name")["price_ref"]
      .mean()
      .sort_values(ascending=False)
      .head(20)
)

print(avg_effect_price)


#--------------------------------------
# Most expensive taunts
#--------------------------------------

print("=" * 60)
print("Top 20 Most Expensive Taunts")
print("=" * 60)

print(df[df["item_type"] == "taunt"].nlargest(
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
print("\nAverage price by item type:")
print("=" * 60)

print(
    df.groupby("item_type")["price_ref"]
      .mean()
)