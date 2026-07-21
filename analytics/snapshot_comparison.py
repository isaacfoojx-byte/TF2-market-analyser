from pathlib import Path

from utils import (
    load_latest_data,
    load_data,
    get_latest_pair,
    PRICE_COL,
    PRICE_UNIT
)


def build_comparison():
    old_file, new_file = get_latest_pair()

    old_df, old_priced = load_data(old_file)
    new_df, new_priced = load_data(new_file)

    comparison = old_priced.merge(
        new_priced,
        on=["effect_id", "defindex"],
        suffixes=("_old", "_new"),
        how="outer",
        indicator=True
    )

    return comparison

def calculate_changes(comparison):

    comparison["key_change"] = (
        comparison[f"{PRICE_COL}_new"]
        - comparison[f"{PRICE_COL}_old"]
    )

    comparison["percent_change"] = (
        comparison["key_change"]
        / comparison[f"{PRICE_COL}_old"]
    ) * 100

    return comparison

def classify_changes(comparison):

    comparison["status"] = "Unchanged"

    comparison.loc[
        comparison["_merge"] == "right_only",
        "status"
    ] = "New Listing"

    comparison.loc[
        comparison["_merge"] == "left_only",
        "status"
    ] = "Removed"

    comparison.loc[
        comparison["key_change"] > 0,
        "status"
    ] = "Price Increased"

    comparison.loc[
        comparison["key_change"] < 0,
        "status"
    ] = "Price Decreased"
    
    return comparison

def print_summary(comparison):

    print("=" * 60)
    print("Market Summary")
    print("=" * 60)

    print(f"Total listings: {len(comparison):,}")

    print(f"New listings: {(comparison['_merge'] == 'right_only').sum()}")

    print(f"Removed listings: {(comparison['_merge'] == 'left_only').sum()}")

    print(f"Price increases: {(comparison['key_change'] > 0).sum()}")

    print(f"Price decreases: {(comparison['key_change'] < 0).sum()}")


def print_top_movers(comparison):

    print("=" * 60)
    print("Top 10 Gainers")
    print("=" * 60)

    print(
        comparison.nlargest(
            10,
            "key_change"
        )[
            [
                "effect_name_new",
                "item_name_new",
                f"{PRICE_COL}_old",
                f"{PRICE_COL}_new",
                "key_change",
                "percent_change"
            ]
        ]
    )

    print("=" * 60)
    print("Top 10 Losers")
    print("=" * 60)

    print(
        comparison.nsmallest(
            10,
            "key_change"
        )[
            [
                "effect_name_new",
                "item_name_new",
                f"{PRICE_COL}_old",
                f"{PRICE_COL}_new",
                "key_change",
                "percent_change"
            ]
        ]
    )


def save_results(comparison):

    output = Path("data/comparisons")

    output.mkdir(
        parents=True,
        exist_ok=True
    )

    comparison.to_csv(
        output / "latest_comparison.csv",
        index=False
    )

def main():

    comparison = build_comparison()

    comparison = calculate_changes(comparison)

    comparison = classify_changes(comparison)

    print_summary(comparison)

    print_top_movers(comparison)

    save_results(comparison)