import pandas as pd


def generate_item_insights(
    item_summary: pd.DataFrame,
) -> list[str]:

    insights = []

    biggest = item_summary.loc[
        item_summary["average_change"].idxmax()
    ]

    worst = item_summary.loc[
        item_summary["average_change"].idxmin()
    ]

    insights.append(
        f"Best-performing item: {biggest['item_name']} ({biggest['average_change']:.2f}%)."
    )

    insights.append(
        f"Largest decline: {worst['item_name']} ({worst['average_change']:.2f}%)."
    )

    return insights