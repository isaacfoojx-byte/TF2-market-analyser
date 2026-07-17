import pandas as pd
import numpy as np

df = pd.read_csv("data/all_unusuals.csv")

# --------------------------------------
# Feature Engineering
# --------------------------------------

# Default classification
df["item_type"] = "unknown"

# Categorize items based on slot
df.loc[df["slot"] == "misc", "item_type"] = "cosmetic"
df.loc[df["slot"] == "taunt", "item_type"] = "taunt"
df.loc[
    df["slot"].isin(["primary", "secondary", "melee"]),
    "item_type"
] = "weapon"

# Generic War Paint rows have no slot
df.loc[df["item_name"] == "War Paint", "item_type"] = "war_paint"

# Replace missing market prices with NaN
df.loc[df["price_ref"] == 0, "price_ref"] = np.nan

# Convenience column
df["has_price"] = df["price_ref"].notna()

# --------------------------------------
# Save the cleaned data
# --------------------------------------

print("=" * 60)
print("Saving Cleaned Data")
print("=" * 60)

df.to_csv(
    "data/cleaned_unusuals.csv",
    index=False
)

print("Saved cleaned dataset.")