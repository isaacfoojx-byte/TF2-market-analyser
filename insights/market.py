import pandas as pd

from .common import percentage


def generate_market_insights(
    comparison: pd.DataFrame,
    summary: pd.Series,
) -> list[str]:

    insights = []

    total = int(summary["total_unusuals"])

    gainers = int(summary["price_up"])

    losers = int(summary["price_down"])

    unchanged = int(summary["unchanged"])

    insights.append(
        f"{percentage(gainers, total):.1f}% of listings increased in price."
    )

    insights.append(
        f"{percentage(losers, total):.1f}% of listings decreased in price."
    )

    insights.append(
        f"{unchanged:,} listings remained unchanged."
    )

    return insights