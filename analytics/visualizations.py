import pandas as pd
import matplotlib.pyplot as plt
import os

df = pd.read_csv("data/processed/cleaned_unusuals.csv")

priced = df[df["has_price"]].copy()

plt.rcParams["figure.figsize"] = (10, 6)

os.makedirs("figures", exist_ok=True)

def save_plot(filename):
    plt.tight_layout()
    plt.savefig(
        f"figures/{filename}",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

# -------------------------------------------------------
# 1. Distribution of Prices
# -------------------------------------------------------

plt.figure()

plt.hist(priced["price_ref"], bins=100)

plt.title("Distribution of Unusual Prices")
plt.xlabel("Price (Refined)")
plt.ylabel("Number of Listings")

plt.tight_layout()

save_plot("unusual_price_distribution.png")

plt.show()


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

save_plot("rarity_vs_price.png")


plt.show()



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

save_plot("top_20_effects_by_average_price.png")


plt.show()



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

save_plot("top_20_items_by_average_price.png")

plt.show()



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

save_plot("average_price_by_item_type.png")

plt.show()


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

save_plot("most_common_effects.png")

plt.show()


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

save_plot("most_common_items.png")

plt.show()



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

save_plot("price_distribution_by_item_type.png")


plt.show()

#-------------------------------------------------------
# Calculating Coefficient of Variation for Effects
#-------------------------------------------------------

effect_stats = (
    priced.groupby("effect_name")
          .agg(
              listings=("price_ref", "count"),
              average_price=("price_ref", "mean"),
              std_dev=("price_ref", "std")
          )
)

effect_stats["coefficient_of_variation"] = (
    effect_stats["std_dev"] /
    effect_stats["average_price"]
)

#-------------------------------------------------------
# Removing effects with fewer than 50 listings to ensure statistical significance
#-------------------------------------------------------

effect_stats = effect_stats[
    effect_stats["listings"] >= 50
]

#-------------------------------------------------------
# 9. Top 20 Most Stable Effects
#-------------------------------------------------------

stable_effects = (
    effect_stats
        .sort_values("coefficient_of_variation")
        .head(20)
)

plt.figure(figsize=(12,8))

stable_effects.sort_values("coefficient_of_variation").plot(
    kind="barh",
    y="coefficient_of_variation",
    legend=False
)

plt.title("20 Most Stable Effects")
plt.xlabel("Coefficient of Variation")
plt.ylabel("Effect")

plt.tight_layout()

plt.savefig(
    "figures/most_stable_effects.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

#-------------------------------------------------------
# 10. Top 20 Most Volatile Effects
#-------------------------------------------------------
volatile_effects = (
    effect_stats
        .sort_values(
            "coefficient_of_variation",
            ascending=False
        )
        .head(20)
)

plt.figure(figsize=(12,8))

volatile_effects.sort_values("coefficient_of_variation").plot(
    kind="barh",
    y="coefficient_of_variation",
    legend=False
)

plt.title("20 Most Volatile Effects")
plt.xlabel("Coefficient of Variation")
plt.ylabel("Effect")

plt.tight_layout()

plt.savefig(
    "figures/most_volatile_effects.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()