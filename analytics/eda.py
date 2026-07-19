import pandas as pd

df = pd.read_csv("data/processed/cleaned_unusuals.csv")

# "eda" stands for Exploratory Data Analysis, which is the process of analyzing and summarizing datasets to gain insights and understand their characteristics. In this code snippet, we are performing EDA on a dataset of unusual items in a game.

#--------------------------------------
# Data Inspection
#--------------------------------------

print(df.info())
print(df.describe())
print(df.head())

print(df["item_type"].value_counts())

print("Average price by item type:")
print(df.groupby("item_type")["price_ref"].mean())

print("Items per effect:")
print(df.groupby("effect_name").size().sort_values(ascending=False))

print("Rows with missing 'slot':")
print(df[df["slot"].isna()])

print("Maximum existence:")
print(df.loc[df["exist"].idxmax()])

print("Missing price count by item type:")
print(df[df["price_ref"].isna()]["item_type"].value_counts())

print("Number of items with 0 recorded items in existence:")
print("Items with exist == 0:", (df["exist"] == 0).sum())

print("Sample rows with missing prices:")
print(
    df[df["price_ref"].isna()][
        ["effect_name", "item_name", "exist", "item_type"]
    ].head(30)
)






