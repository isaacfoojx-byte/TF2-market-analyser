from pathlib import Path
import pandas as pd

from analytics.utils import (
    load_data,
    get_latest_pair,
    PRICE_COL,
)


def build_comparison():
    old_file, new_file = get_latest_pair()

    old_df, old_priced = load_data(old_file)
    new_df, new_priced = load_data(new_file)

    old_market = (
    old_priced
    .groupby(
        ["effect_id", "effect_name",
         "defindex", "item_name"]
    )
    .agg(
        listings=("effect_id", "count"),
        average_price=(PRICE_COL, "mean"),
        median_price=(PRICE_COL, "median")
    )
    .reset_index()
    )

    new_market = (
        new_priced
        .groupby(
            ["effect_id", "effect_name",
            "defindex", "item_name"]
        )
        .agg(
            listings=("effect_id", "count"),
            average_price=(PRICE_COL, "mean"),
            median_price=(PRICE_COL, "median")
        )
        .reset_index()
    )

    comparison = old_market.merge(
        new_market,
        on=[
            "effect_id",
            "effect_name",
            "defindex",
            "item_name"
        ],
        how="outer",
        suffixes=("_old", "_new"),
        indicator=True
    )

    return comparison

def calculate_changes(comparison):

    # comparison["key_change"] = (
    #     comparison[f"{PRICE_COL}_new"]
    #     - comparison[f"{PRICE_COL}_old"]
    # )

    # comparison["percent_change"] = (
    #     comparison["key_change"]
    #     / comparison[f"{PRICE_COL}_old"]
    # ) * 100

    # return comparison

    comparison["price_change"] = (
    comparison["average_price_new"]
    - comparison["average_price_old"]
)

    comparison["percent_change"] = (
        comparison["price_change"]
        / comparison["average_price_old"]
    ) * 100

    comparison["percent_change"] = (
        comparison["percent_change"]
        .replace([float("inf"), float("-inf")], pd.NA)
    )

    comparison["listing_change"] = (
        comparison["listings_new"]
        - comparison["listings_old"]
    )

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
        comparison["price_change"] > 0,
        "status"
    ] = "Price Increased"

    comparison.loc[
        comparison["price_change"] < 0,
        "status"
    ] = "Price Decreased"
    
    return comparison

def format_market_summary(comparison):

    lines = []

    lines.append("=" * 60)
    lines.append("Market Summary")
    lines.append("=" * 60)

    lines.append(
        f"Unique unusual markets: {len(comparison):,}"
    )

    lines.append(
        f"New listings: {(comparison['_merge'] == 'right_only').sum()}"
    )

    lines.append(
        f"Net listing change: "
        f"{comparison['listing_change'].sum():+,.0f}"
    )

    lines.append(
        f"Removed listings: {(comparison['_merge'] == 'left_only').sum()}"
    )

    lines.append(
        f"Price increases: {(comparison['price_change'] > 0).sum()}"
    )

    lines.append(
        f"Price decreases: {(comparison['price_change'] < 0).sum()}"
    )

    return "\n".join(lines)

def format_top_movers(comparison):

    lines = []

    lines.append("=" * 60)
    lines.append("Top 10 Gainers")
    lines.append("=" * 60)

    gainers = comparison.nlargest(
        10,
        "price_change"
    )[
        [
            "effect_name",
            "item_name",
            "average_price_old",
            "average_price_new",
            "price_change",
            "percent_change"
        ]
    ]

    lines.append(gainers.to_string(index=False))

    lines.append("")

    lines.append("=" * 60)
    lines.append("Top 10 Losers")
    lines.append("=" * 60)

    losers = comparison.nsmallest(
        10,
        "price_change"
    )[
        [
            "effect_name",
            "item_name",
            "average_price_old",
            "average_price_new",
            "price_change",
            "percent_change"
        ]
    ]

    lines.append(losers.to_string(index=False))

    return "\n".join(lines)


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

    comparison.query(
        "status in ['Price Increased','Price Decreased']"
    ).to_csv(
        output / "price_changes.csv",
        index=False
    )

    comparison.query(
        "status == 'New Listing'"
    ).to_csv(
        output / "new_listings.csv",
        index=False
    )

    comparison.query(
        "status == 'Removed'"
    ).to_csv(
        output / "removed_listings.csv",
        index=False
    )

    comparison.query(
        "status == 'Unchanged'"
    ).to_csv(
        output / "unchanged.csv",
        index=False
    )

def build_effect_summary(comparison):

    effect_summary = (
        comparison
        .groupby("effect_name")
        .agg(
            unusuals=("effect_name", "count"),
            average_change=("price_change", "mean"),
            median_change=("price_change", "median"),
            average_listing_change=("listing_change", "mean"),
            increases=("status",
                       lambda s: (s == "Price Increased").sum()),
            decreases=("status",
                       lambda s: (s == "Price Decreased").sum()),
            new=("status",
                 lambda s: (s == "New Listing").sum()),
            removed=("status",
                     lambda s: (s == "Removed").sum()),
            
        )
        .reset_index()
    )

    return effect_summary

def save_effect_summary(effect_summary):

    output = Path("data/comparisons")

    output.mkdir(
        parents=True,
        exist_ok=True
    )

    effect_summary.to_csv(
        output / "effect_summary.csv",
        index=False
    )

def build_item_summary(comparison):

    item_summary = (
        comparison
        .groupby("item_name")
        .agg(
            unusuals=("item_name", "count"),
            average_change=("price_change", "mean"),
            median_change=("price_change", "median"),
            average_listing_change=("listing_change", "mean"),
            increases=("status",
                       lambda s: (s == "Price Increased").sum()),
            decreases=("status",
                       lambda s: (s == "Price Decreased").sum()),
            new=("status",
                 lambda s: (s == "New Listing").sum()),
            removed=("status",
                     lambda s: (s == "Removed").sum())
        )
        .reset_index()
    )

    return item_summary

def save_item_summary(item_summary):

    output = Path("data/comparisons")

    output.mkdir(
        parents=True,
        exist_ok=True
    )

    item_summary.to_csv(
        output / "item_summary.csv",
        index=False
    )

def build_market_summary(comparison):

    summary = {
        "total_unusuals": len(comparison),

        "new_listings":
            (comparison["status"] == "New Listing").sum(),

        "removed":
            (comparison["status"] == "Removed").sum(),

        "price_up":
            (comparison["status"] == "Price Increased").sum(),

        "price_down":
            (comparison["status"] == "Price Decreased").sum(),

        "unchanged":
            (comparison["status"] == "Unchanged").sum(),

        "average_change":
            comparison["price_change"].mean(),

        "median_change":
            comparison["price_change"].median(),

        "average_listing_change":
            comparison["listing_change"].mean(),

        "largest_listing_gain":
            comparison["listing_change"].max(),

        "largest_listing_loss":
            comparison["listing_change"].min(),

        "largest_gain":
            comparison["price_change"].max(),

        "largest_loss":
            comparison["price_change"].min()
    }

    return pd.DataFrame([summary])

def save_market_summary(market_summary):

    output = Path("data/comparisons")

    output.mkdir(
        parents=True,
        exist_ok=True
    )

    market_summary.to_csv(
        output / "market_summary.csv",
        index=False
    )

def update_market_history(market_summary):

    output = Path("data/comparisons")

    output.mkdir(
        parents=True,
        exist_ok=True
    )

    history_file = output / "market_history.csv"

    market_summary.to_csv(
        history_file,
        mode="a",
        header=not history_file.exists(),
        index=False
    )

def main():

    comparison = build_comparison()

    comparison = calculate_changes(comparison)

    comparison = classify_changes(comparison)

    effect_summary = build_effect_summary(comparison)

    item_summary = build_item_summary(comparison)

    market_summary = build_market_summary(comparison)

    print(format_market_summary(comparison))

    print()

    print(format_top_movers(comparison))

    save_results(comparison)

    save_effect_summary(effect_summary)

    save_item_summary(item_summary)

    save_market_summary(market_summary)

    update_market_history(market_summary)