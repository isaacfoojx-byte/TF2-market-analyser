from analytics.utils import (
    load_latest_data,
    PRICE_COL,
    PRICE_UNIT
)

df, priced = load_latest_data()

# "eda" stands for Exploratory Data Analysis, which is the process of analyzing and summarizing datasets to gain insights and understand their characteristics. In this code snippet, we are performing EDA on a dataset of unusual items in a game.

#--------------------------------------
# Data Inspection
#--------------------------------------

print(df.info())
print(df.describe())
print(df.head())

print(df["item_type"].value_counts())

print("Average price by item type:")
print(df.groupby("item_type")[PRICE_COL].mean())

print("Items per effect:")
print(df.groupby("effect_name").size().sort_values(ascending=False))

print("Rows with missing 'slot':")
print(df[df["slot"].isna()])

print("Missing price count by item type:")
print(df[df[PRICE_COL].isna()]["item_type"].value_counts())

print("Sample rows with missing prices:")
print(
    df[df[PRICE_COL].isna()][
        ["effect_name", "item_name", "item_type"]
    ].head(30)
)






