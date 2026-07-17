import pandas as pd
import matplotlib.pyplot as plt
import os

df = pd.read_csv("data/cleaned_unusuals.csv")

priced = df[df["has_price"]].copy()

plt.rcParams["figure.figsize"] = (10, 6)

os.makedirs("figures", exist_ok=True)

# -------------------------------------------------------
# 1. Distribution of Prices
# -------------------------------------------------------

plt.figure()

plt.hist(priced["price_ref"], bins=100)

plt.title("Distribution of Unusual Prices")
plt.xlabel("Price (Refined)")
plt.ylabel("Number of Listings")

plt.tight_layout()
plt.show()

plt.savefig("figures/unusual_price_distribution.png", dpi=300)
# -------------------------------------------------------
# 2. Rarity vs Price
# -------------------------------------------------------

plt.figure()

plt.scatter(
    priced["exist"],
    priced["price_ref"],
    alpha=0.3
)

plt.title("Rarity vs Price")
plt.xlabel("Existence")
plt.ylabel("Price (Refined)")

plt.tight_layout()
plt.show()

plt.savefig("figures/rarity_vs_price.png", dpi=300)

# -------------------------------------------------------
# 3. Top 20 Effects by Average Price
# -------------------------------------------------------

effect_avg = (
    priced.groupby("effect_name")["price_ref"]
          .mean()
          .sort_values(ascending=False)
          .head(20)
)

plt.figure(figsize=(12,8))

effect_avg.sort_values().plot(kind="barh")

plt.title("Top 20 Effects by Average Price")
plt.xlabel("Average Price (Refined)")
plt.ylabel("Effect")

plt.tight_layout()
plt.show()

plt.savefig("figures/top_20_effects_by_average_price.png", dpi=300)

# -------------------------------------------------------
# 4. Top 20 Items by Average Price
# -------------------------------------------------------

item_avg = (
    priced.groupby("item_name")["price_ref"]
          .mean()
          .sort_values(ascending=False)
          .head(20)
)

plt.figure(figsize=(12,8))

item_avg.sort_values().plot(kind="barh")

plt.title("Top 20 Items by Average Price")
plt.xlabel("Average Price (Refined)")
plt.ylabel("Item")

plt.tight_layout()
plt.show()

plt.savefig("figures/top_20_items_by_average_price.png", dpi=300)

# -------------------------------------------------------
# 5. Average Price by Item Type
# -------------------------------------------------------

item_type = (
    priced.groupby("item_type")["price_ref"]
          .mean()
)

plt.figure()

item_type.plot(kind="bar")

plt.title("Average Price by Item Type")
plt.xlabel("Item Type")
plt.ylabel("Average Price (Refined)")

plt.tight_layout()
plt.show()

plt.savefig("figures/average_price_by_item_type.png", dpi=300)
# -------------------------------------------------------
# 6. Top 20 Most Common Effects
# -------------------------------------------------------

effect_count = (
    priced["effect_name"]
          .value_counts()
          .head(20)
)

plt.figure(figsize=(12,8))

effect_count.sort_values().plot(kind="barh")

plt.title("Most Common Effects")
plt.xlabel("Number of Listings")

plt.tight_layout()
plt.show()

plt.savefig("figures/most_common_effects.png", dpi=300)
# -------------------------------------------------------
# 7. Top 20 Most Common Items
# -------------------------------------------------------

item_count = (
    priced["item_name"]
          .value_counts()
          .head(20)
)

plt.figure(figsize=(12,8))

item_count.sort_values().plot(kind="barh")

plt.title("Most Common Items")
plt.xlabel("Number of Listings")

plt.tight_layout()
plt.show()

plt.savefig("figures/most_common_items.png", dpi=300)

# -------------------------------------------------------
# 8. Price Distribution by Item Type
# -------------------------------------------------------

plt.figure()

priced.boxplot(
    column="price_ref",
    by="item_type"
)

plt.title("Price Distribution by Item Type")
plt.suptitle("")
plt.xlabel("Item Type")
plt.ylabel("Price (Refined)")

plt.tight_layout()
plt.show()

plt.savefig("figures/price_distribution_by_item_type.png", dpi=300)