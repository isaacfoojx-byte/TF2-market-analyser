import pandas as pd
import numpy as np

df = pd.read_csv("data/all_unusuals.csv")

# --------------------------------------
# Feature Engineering
# --------------------------------------

df["item_type"] = "cosmetic"

df.loc[
    df["item_name"].str.startswith("Taunt:"),
    "item_type"
] = "taunt"

df.loc[
    df["item_name"] == "War Paint",
    "item_type"
] = "war_paint"

df.loc[df["price_ref"] == 0, "price_ref"] = np.nan

df["has_price"] = df["price_ref"].notna()

pd.crosstab(
    df["exist"] == 0,
    df["price_ref"] == 0
)

#--------------------------------------
# Save the cleaned data
#--------------------------------------

df.to_csv(
    "data/cleaned_unusuals.csv",
    index=False
)

print("Saved cleaned dataset.")