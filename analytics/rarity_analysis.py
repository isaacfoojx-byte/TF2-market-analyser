import pandas as pd

df = pd.read_csv("data/cleaned_unusuals.csv")

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.precision", 2)

unique_df = df[df["exist"] == 1]
cosmetics = df[df["item_type"] == "cosmetic"]
taunts = df[df["item_type"] == "taunt"]
non_war_paints = df[df["item_type"] != "war_paint"]

#--------------------------------------
# Existence Statistics
#--------------------------------------

print("=" * 60)
print("Existence Statistics")
print("=" * 60)

print(df["exist"].describe())

#--------------------------------------
# Distribution of Existence Counts
#--------------------------------------

print("=" * 60)
print("Distribution of Existence Counts")
print("=" * 60)

print(df["exist"].value_counts().sort_index())


#--------------------------------------
# Unique Unusuals (exist == 1) (Top 20 by Price)
#--------------------------------------
print("=" * 60)
print("Unique Unusuals (exist == 1) (Top 20 by Price)")
print("=" * 60)

print(
    unique_df[[
        "effect_name",
        "item_name",
        "price_ref",
        "item_type"
    ]]
    .sort_values("price_ref", ascending=False).head(20)
)

print(f"Total unique unusuals: {len(unique_df):,}")


#--------------------------------------
# Average Price by Existence Count
#--------------------------------------

print("=" * 60)
print("Average Price by Existence Count")
print("=" * 60)

avg_price_by_exist = (
    df.groupby("exist")["price_ref"]
      .mean()
      .sort_index()
      .round(2)
)

print(avg_price_by_exist.head(30))

#--------------------------------------
# Correlation between Existence and Price
#--------------------------------------

print("=" * 60)
print("Correlation between Existence and Price")
print("=" * 60)

corr = df["exist"].corr(df["price_ref"])

print(f"Pearson correlation: {corr:.3f}")

if corr < -0.7:
    print("Strong negative relationship")
elif corr < -0.3:
    print("Moderate negative relationship")
elif corr < 0:
    print("Weak negative relationship")

#--------------------------------------
# Average Price by Existence (Cosmetics)
#--------------------------------------

print("=" * 60)
print("Average Price by Existence (Cosmetics)")
print("=" * 60)

print(
    cosmetics
      .groupby("exist")["price_ref"]
      .mean()
      .sort_index()
      .round(2)
      .head(20)
)


#--------------------------------------
# Average Price by Existence (Taunts)
#--------------------------------------

print("=" * 60)
print("Average Price by Existence (Taunts)")
print("=" * 60)

print(
    taunts
      .groupby("exist")["price_ref"]
      .mean()
      .sort_index()
      .round(2)
      .head(20)
)

#--------------------------------------
# Cheapest Unique Unusuals (Top 20 by Price))
#--------------------------------------

print("=" * 60)
print("Cheapest Unique Unusuals (Top 20 by Price)")
print("=" * 60)

print(
    unique_df[[
        "effect_name",
        "item_name",
        "price_ref",
        "item_type"
    ]]
    .sort_values("price_ref")
    .head(20)
)

#--------------------------------------
# Top 20 Most Common Unusuals (excluding war paints)
#--------------------------------------

print("=" * 60)
print("Top 20 Most Common Unusuals")
print("=" * 60)

print(
    non_war_paints.nlargest(
        20,
        "exist"
    )[[
        "effect_name",
        "item_name",
        "exist",
        "price_ref"
    ]]
)

#--------------------------------------
# Top 20 Most Common Cosmetic Unusuals
#--------------------------------------

print("=" * 60)
print("Top 20 Most Common Cosmetic Unusuals")
print("=" * 60)

print(
    df[df["slot"] == "misc"]
    .nlargest(
        20,
        "exist"
    )[[
        "effect_name",
        "item_name",
        "exist",
        "price_ref"
    ]]
)