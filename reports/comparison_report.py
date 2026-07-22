from analytics.snapshot_comparison import (
    build_comparison,
    calculate_changes,
    classify_changes,
    build_effect_summary,
    build_item_summary,
    format_market_summary,
    format_top_movers
)

from reports.pdf_report import save_pdf

from reports.report_utils import section, subsection, dataframe, save_text

from reports.report_config import (
    OUTPUT_DIR,
    TEXT_FILENAME,
)

filename = OUTPUT_DIR / TEXT_FILENAME


def format_effect_summary(effect_summary):

    lines = []

    
    lines.append(section("Effect Summary"))
    
    

    lines.append(subsection("Top 10 Effects by Average Price Increase"))
    

    top_gainers = (
        effect_summary
        .nlargest(10, "average_change")[
            [
                "effect_name",
                "average_change"
            ]
        ]
    )

    lines.append(dataframe(top_gainers))
    

    lines.append(subsection("Top 10 Most Active Effects"))
    
    most_active = (
        effect_summary
        .nlargest(10, "unusuals")[
            [
                "effect_name",
                "unusuals"
            ]
        ]
    )

    lines.append(dataframe(most_active))
    

    lines.append(subsection("Top 10 Effects with Most Price Increases"))
    

    increases = (
        effect_summary
        .nlargest(10, "increases")[
            [
                "effect_name",
                "increases"
            ]
        ]
    )

    lines.append(dataframe(increases))


    
    lines.append(subsection("Top 10 Effects by Average Listing Increase"))
   

    listing = (
        effect_summary
        .nlargest(10, "average_listing_change")[
            [
                "effect_name",
                "average_listing_change"
            ]
        ]
    )

    lines.append(dataframe(listing))

    return "\n".join(lines)

def format_item_summary(item_summary):

    lines = []

    
    lines.append(section("Item Summary"))
    
    

    lines.append(subsection("Top 10 Items by Average Price Increase"))
    

    top_gainers = (
        item_summary
        .nlargest(10, "average_change")[
            [
                "item_name",
                "average_change"
            ]
        ]
    )

    lines.append(dataframe(top_gainers))
    

    lines.append(subsection("Top 10 Most Active Items"))
    

    most_active = (
        item_summary
        .nlargest(10, "unusuals")[
            [
                "item_name",
                "unusuals"
            ]
        ]
    )

    lines.append(dataframe(most_active))
    

    lines.append(subsection("Top 10 Items with Most Price Increases"))
    

    increases = (
        item_summary
        .nlargest(10, "increases")[
            [
                "item_name",
                "increases"
            ]
        ]
    )

    lines.append(dataframe(increases))

    lines.append(subsection("Top 10 Items by Average Listing Increase"))
    

    listing = (
        item_summary
        .nlargest(10, "average_listing_change")[
            [
                "item_name",
                "average_listing_change"
            ]
        ]
    )

    lines.append(dataframe(listing))

    return "\n".join(lines)



def build_report():

    comparison = build_comparison()

    comparison = calculate_changes(comparison)

    comparison = classify_changes(comparison)

    effect_summary = build_effect_summary(comparison)

    item_summary = build_item_summary(comparison)


    report = []

    report.append(section("TF2 MARKET COMPARISON REPORT"))
    

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

    filename = OUTPUT_DIR / "comparison_report.txt"

    save_text(report, filename)

# In order to run the main() function, you have to use the command in VSCode "python -m reports.comparison_report", or else python will not recognise the imports from the analytics.snapshot_comparison.py file.
def main():

    report = build_report()

    print(report)

    save_report(report)

    save_pdf(report)


if __name__ == "__main__":
    main()