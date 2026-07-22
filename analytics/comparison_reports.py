from pathlib import Path

from snapshot_comparison import (
    build_comparison,
    calculate_changes,
    classify_changes,
    build_effect_summary,
    build_item_summary,
    build_market_summary,
    format_market_summary,
    format_top_movers
)

OUTPUT = Path("reports")

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)

def format_effect_summary(effect_summary):

    lines = []

    lines.append("=" * 60)
    lines.append("Effect Summary")
    lines.append("=" * 60)
    lines.append("")

    lines.append("Top 10 Effects by Average Price Increase")
    lines.append("-" * 60)

    top_gainers = (
        effect_summary
        .nlargest(10, "average_change")[
            [
                "effect_name",
                "average_change"
            ]
        ]
    )

    lines.append(top_gainers.to_string(index=False))
    lines.append("")

    lines.append("Top 10 Most Active Effects")
    lines.append("-" * 60)

    most_active = (
        effect_summary
        .nlargest(10, "unusuals")[
            [
                "effect_name",
                "unusuals"
            ]
        ]
    )

    lines.append(most_active.to_string(index=False))
    lines.append("")

    lines.append("Top 10 Effects with Most Price Increases")
    lines.append("-" * 60)

    increases = (
        effect_summary
        .nlargest(10, "increases")[
            [
                "effect_name",
                "increases"
            ]
        ]
    )

    lines.append(increases.to_string(index=False))


    lines.append("")
    lines.append("Top 10 Effects by Average Listing Increase")
    lines.append("-" * 60)

    listing = (
        effect_summary
        .nlargest(10, "average_listing_change")[
            [
                "effect_name",
                "average_listing_change"
            ]
        ]
    )

    lines.append(listing.to_string(index=False))

    return "\n".join(lines)

def format_item_summary(item_summary):

    lines = []

    lines.append("=" * 60)
    lines.append("Item Summary")
    lines.append("=" * 60)
    lines.append("")

    lines.append("Top 10 Items by Average Price Increase")
    lines.append("-" * 60)

    top_gainers = (
        item_summary
        .nlargest(10, "average_change")[
            [
                "item_name",
                "average_change"
            ]
        ]
    )

    lines.append(top_gainers.to_string(index=False))
    lines.append("")

    lines.append("Top 10 Most Active Items")
    lines.append("-" * 60)

    most_active = (
        item_summary
        .nlargest(10, "unusuals")[
            [
                "item_name",
                "unusuals"
            ]
        ]
    )

    lines.append(most_active.to_string(index=False))
    lines.append("")

    lines.append("Top 10 Items with Most Price Increases")
    lines.append("-" * 60)

    increases = (
        item_summary
        .nlargest(10, "increases")[
            [
                "item_name",
                "increases"
            ]
        ]
    )

    lines.append(increases.to_string(index=False))


    lines.append("")
    lines.append("Top 10 Items by Average Listing Increase")
    lines.append("-" * 60)

    listing = (
        item_summary
        .nlargest(10, "average_listing_change")[
            [
                "item_name",
                "average_listing_change"
            ]
        ]
    )

    lines.append(listing.to_string(index=False))

    return "\n".join(lines)



def build_report():

    comparison = build_comparison()

    comparison = calculate_changes(comparison)

    comparison = classify_changes(comparison)

    effect_summary = build_effect_summary(comparison)

    item_summary = build_item_summary(comparison)


    report = []

    report.append("=" * 60)
    report.append("TF2 MARKET COMPARISON REPORT")
    report.append("=" * 60)
    report.append("")

    report.append(
        format_market_summary(comparison)
    )

    report.append("")

    report.append(
        format_top_movers(comparison)
    )

    report.append("")

    report.append(
    format_effect_summary(effect_summary)
    )

    report.append("")

    report.append(
    format_item_summary(item_summary)
    )

    report.append("")

    return "\n\n".join(report)



def save_report(report):

    filename = (
        OUTPUT /
        "comparison_report.txt"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)


def main():

    report = build_report()

    print(report)

    save_report(report)


if __name__ == "__main__":
    main()