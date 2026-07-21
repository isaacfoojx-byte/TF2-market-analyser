from pathlib import Path

import matplotlib.pyplot as plt

from snapshot_comparison import (
    build_comparison,
    calculate_changes,
    classify_changes,
    build_effect_summary,
    build_item_summary
)

OUTPUT = Path("figures/comparison")

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)

# Plot charts using effect_summary and item_summary

def plot_biggest_gainers(comparison):

    top = (
        comparison
        .nlargest(10, "price_change")
        .sort_values("price_change")
    )

    plt.figure(figsize=(10,6))

    plt.barh(
        top["item_name"],
        top["price_change"]
    )

    plt.xlabel("Price Change (Keys)")
    plt.ylabel("Item")
    plt.title("Top 10 Biggest Price Increases")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "biggest_gainers.png",
        dpi=300
    )

    plt.close()


def plot_biggest_losers(comparison):

    bottom = (
        comparison
        .nsmallest(10, "price_change")
        .sort_values("price_change")
    )

    plt.figure(figsize=(10,6))

    plt.barh(
        bottom["item_name"],
        bottom["price_change"]
    )

    plt.xlabel("Price Change (Keys)")
    plt.ylabel("Item")
    plt.title("Top 10 Biggest Price Decreases")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "biggest_losers.png",
        dpi=300
    )

    plt.close()

def plot_price_distribution(comparison):

    plt.figure(figsize=(8,6))

    plt.hist(
        comparison["price_change"].dropna(),
        bins=30
    )

    plt.xlabel("Price Change (Keys)")
    plt.ylabel("Count")

    plt.title("Distribution of Price Changes")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "price_distribution.png",
        dpi=300
    )

    plt.close()

def plot_effect_changes(effect_summary):

    top = (
        effect_summary
        .nlargest(15, "average_change")
        .sort_values("average_change")
    )

    plt.figure(figsize=(10,8))

    plt.barh(
        top["effect_name"],
        top["average_change"]
    )

    plt.xlabel("Average Change (Keys)")
    plt.ylabel("Effect")

    plt.title("Effects with Largest Average Price Increase")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "effect_changes.png",
        dpi=300
    )

    plt.close()


def plot_item_changes(item_summary):

    top = (
        item_summary
        .nlargest(15, "average_change")
        .sort_values("average_change")
    )

    plt.figure(figsize=(10,8))

    plt.barh(
        top["item_name"],
        top["average_change"]
    )

    plt.xlabel("Average Change (Keys)")
    plt.ylabel("Item")

    plt.title("Items with Largest Average Price Increase")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "item_changes.png",
        dpi=300
    )

    plt.close()

def plot_listing_changes(comparison):

    top = (
        comparison
        .nlargest(15, "listing_change")
        .sort_values("listing_change")
    )

    plt.figure(figsize=(10,8))

    plt.barh(
        top["item_name"],
        top["listing_change"]
    )

    plt.xlabel("Listing Change")
    plt.ylabel("Item")

    plt.title("Largest Increase in Listings")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "listing_changes.png",
        dpi=300
    )

    plt.close()


def plot_market_status(comparison):

    status_counts = (
        comparison["status"]
        .value_counts()
        .sort_index()
    )

    plt.figure(figsize=(8,6))

    plt.bar(
        status_counts.index,
        status_counts.values
    )

    plt.xlabel("Status")
    plt.ylabel("Count")
    plt.title("Market Status Breakdown")

    plt.xticks(rotation=20)

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "market_status.png",
        dpi=300
    )

    plt.close()


def plot_listing_losses(comparison):

    bottom = (
        comparison
        .nsmallest(15, "listing_change")
        .sort_values("listing_change")
    )

    plt.figure(figsize=(10,8))

    plt.barh(
        bottom["item_name"],
        bottom["listing_change"]
    )

    plt.xlabel("Listing Change")
    plt.ylabel("Item")
    plt.title("Largest Decrease in Listings")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "listing_losses.png",
        dpi=300
    )

    plt.close()


def plot_price_vs_listing_change(comparison):

    plt.figure(figsize=(8,6))

    plt.scatter(
        comparison["listing_change"],
        comparison["price_change"],
        alpha=0.6
    )

    plt.axhline(
        0,
        linestyle="--"
    )

    plt.axvline(
        0,
        linestyle="--"
    )

    plt.xlabel("Listing Change")
    plt.ylabel("Price Change (Keys)")
    plt.title("Price Change vs Listing Change")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "price_vs_listing_change.png",
        dpi=300
    )

    plt.close()

def plot_effect_activity(effect_summary):

    top = (
        effect_summary
        .nlargest(15, "unusuals")
        .sort_values("unusuals")
    )

    plt.figure(figsize=(10,8))

    plt.barh(
        top["effect_name"],
        top["unusuals"]
    )

    plt.xlabel("Number of Markets")
    plt.ylabel("Effect")
    plt.title("Most Active Effects")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "effect_activity.png",
        dpi=300
    )

    plt.close()


def plot_item_activity(item_summary):

    top = (
        item_summary
        .nlargest(15, "unusuals")
        .sort_values("unusuals")
    )

    plt.figure(figsize=(10,8))

    plt.barh(
        top["item_name"],
        top["unusuals"]
    )

    plt.xlabel("Number of Markets")
    plt.ylabel("Item")
    plt.title("Most Active Items")

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "item_activity.png",
        dpi=300
    )

    plt.close()


def plot_price_distribution(comparison):

    plt.figure(figsize=(8,6))

    plt.hist(
        comparison["price_change"].dropna(),
        bins=30
    )

    plt.axvline(
        comparison["price_change"].mean(),
        linestyle="--",
        label="Mean"
    )

    plt.xlabel("Price Change (Keys)")
    plt.ylabel("Count")
    plt.title("Distribution of Price Changes")

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "price_distribution.png",
        dpi=300
    )

    plt.close()

def plot_listing_distribution(comparison):

    plt.figure(figsize=(8,6))

    plt.hist(
        comparison["listing_change"].dropna(),
        bins=20
    )

    plt.axvline(
        comparison["listing_change"].mean(),
        linestyle="--",
        label="Mean"
    )

    plt.xlabel("Listing Change")
    plt.ylabel("Count")
    plt.title("Distribution of Listing Changes")

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        OUTPUT / "listing_distribution.png",
        dpi=300
    )

    plt.close()


def main():
    comparison = build_comparison()
    comparison = calculate_changes(comparison)
    comparison = classify_changes(comparison)

    effect_summary = build_effect_summary(comparison)
    item_summary = build_item_summary(comparison)

    plot_biggest_gainers(comparison)
    plot_biggest_losers(comparison)


    plot_price_distribution(comparison)
    plot_effect_changes(effect_summary)

    plot_market_status(comparison)

    plot_effect_changes(effect_summary)
    plot_effect_activity(effect_summary)

    plot_item_changes(item_summary)
    plot_listing_changes(comparison)

    plot_listing_changes(comparison)
    plot_listing_losses(comparison)

    plot_price_vs_listing_change(comparison)