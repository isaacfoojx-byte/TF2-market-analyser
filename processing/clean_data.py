import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime

def parse_key_range(value):

    if pd.isna(value):
        return pd.Series([np.nan, np.nan, np.nan])

    value = value.replace(" keys", "").strip()

    numbers = re.findall(r"\d+(?:\.\d+)?", value)

    if len(numbers) == 2:
        low = float(numbers[0])
        high = float(numbers[1])
    elif len(numbers) == 1:
        low = high = float(numbers[0])
    else:
        return pd.Series([np.nan, np.nan, np.nan])

    mid = (low + high) / 2

    return pd.Series([low, high, mid])


def clean_data(raw_csv,processed_csv,current_key_price):


    df = pd.read_csv(raw_csv)

    df["bp_price_ref"] = df["bp_price_ref"].astype(float)

    df["exist"] = df["exist"].astype(int)

    df["defindex"] = df["defindex"].astype(int)

    df["effect_id"] = df["effect_id"].astype(int)

    # --------------------------------------
    # Feature Engineering
    # --------------------------------------


    df["usd_price"] = (
        df["bp_price_all"]
        .str.extract(r"\$([\d,]+(?:\.\d+)?)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    df[["key_low","key_high","key_mid"]] = (
        df["bp_price_keys"]
        .apply(parse_key_range)
    )

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
    df.loc[df["bp_price_ref"] == 0, "bp_price_ref"] = np.nan

    # Convert refined to keys
    df["bp_price_keys_equivalent"] = (
        df["bp_price_ref"] / current_key_price
    )

    # Convenience column
    df["has_price"] = df["bp_price_ref"].notna()

    # Remove redundant column
    df = df.drop(columns=["bp_price_all"])

    # --------------------------------------
    # Save the cleaned data
    # --------------------------------------

    print("=" * 60)
    print("Saving Cleaned Data")
    print("=" * 60)

    Path(processed_csv).parent.mkdir(
    parents=True,
    exist_ok=True
)

    df.to_csv(
        processed_csv,
        index=False
    )

    print("Saved cleaned dataset.")

if __name__ == "__main__":

    timestamp = "2026-07-21_22-54-09"

    raw_csv = f"data/raw/unusuals_{timestamp}.csv"

    processed_csv = (
        f"data/processed/cleaned_{timestamp}.csv"
    )

    current_key_price = 60.77      # Temporary testing value

    clean_data(
        raw_csv,
        processed_csv,
        current_key_price
    )