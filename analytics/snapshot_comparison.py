"""Latest guide-price comparison; coverage is separate from price movement."""
from pathlib import Path
import pandas as pd

from analytics.comparison import compare_files, comparison_summary
from analytics.utils import get_latest_pair


def build_comparison():
    return compare_files(*get_latest_pair())


def calculate_changes(comparison):
    """The shared comparison engine already computes matched price changes."""
    return comparison.copy()


def classify_changes(comparison):
    return comparison.copy()


def format_market_summary(comparison):
    summary = comparison_summary(comparison)
    return "\n".join(f"{key}: {value}" for key, value in summary.items())


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


def _entity_summary(comparison, column):
    return comparison.groupby(column).agg(
        unusuals=("comparable", "sum"),
        average_change=("price_change", "mean"),
        median_change=("price_change", "median"),
        increases=("status", lambda s: s.eq("Price Increased").sum()),
        decreases=("status", lambda s: s.eq("Price Decreased").sum()),
        entered=("status", lambda s: s.eq("Entered coverage").sum()),
        left=("status", lambda s: s.eq("Left coverage").sum()),
    ).reset_index()


def build_effect_summary(comparison):
    return _entity_summary(comparison, "effect_name")


def build_item_summary(comparison):
    return _entity_summary(comparison, "item_name")


def build_market_summary(comparison):
    return {
        **comparison_summary(comparison),
        "total_unusuals": len(comparison),
        "price_up": int(comparison.status.eq("Price Increased").sum()),
        "price_down": int(comparison.status.eq("Price Decreased").sum()),
        "unchanged": int(comparison.status.eq("Unchanged").sum()),
        "average_change": comparison.price_change.mean(),
        "median_change": comparison.price_change.median(),
        "largest_gain": comparison.price_change.max(),
        "largest_loss": comparison.price_change.min(),
    }


def save_results(comparison):
    output = Path("data/comparisons")
    output.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output / "latest_comparison.csv", index=False)
    for status, name in [("Entered coverage", "entered_coverage"), ("Left coverage", "left_coverage"), ("Unchanged", "unchanged")]:
        comparison.loc[comparison.status.eq(status)].to_csv(output / f"{name}.csv", index=False)
    comparison.loc[comparison.status.isin(["Price Increased", "Price Decreased"])].to_csv(output / "price_changes.csv", index=False)



def _save_summary(frame, filename):
    output = Path("data/comparisons")
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / filename, index=False)


def save_effect_summary(summary):
    _save_summary(summary, "effect_summary.csv")


def save_item_summary(summary):
    _save_summary(summary, "item_summary.csv")


def save_market_summary(summary):
    _save_summary(pd.DataFrame([summary]), "market_summary.csv")


def update_market_history(summary, snapshot_timestamp):
    path = Path("data/comparisons/market_history.csv")
    history = pd.read_csv(path) if path.exists() else pd.DataFrame()
    row = pd.DataFrame([{"snapshot_timestamp": snapshot_timestamp, **summary}])
    history = pd.concat([history, row], ignore_index=True)
    history = history.drop_duplicates("snapshot_timestamp", keep="last").sort_values("snapshot_timestamp")
    _save_summary(history, "market_history.csv")

def main():
    comparison = build_comparison()
    print(format_market_summary(comparison))
    print(format_top_movers(comparison))
    save_results(comparison)
    build_effect_summary(comparison).to_csv("data/comparisons/effect_summary.csv", index=False)
    build_item_summary(comparison).to_csv("data/comparisons/item_summary.csv", index=False)
    summary = build_market_summary(comparison)
    save_market_summary(summary)
    newest = pd.read_csv(comparison.attrs["new_snapshot"], nrows=1)
    update_market_history(summary, newest.iloc[0]["scrape_timestamp"])


if __name__ == "__main__":
    main()
