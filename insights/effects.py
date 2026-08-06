import pandas as pd


def generate_effect_insights(
    effect_summary: pd.DataFrame,
) -> list[str]:

    insights = []

    biggest = effect_summary.loc[
        effect_summary["average_change"].idxmax()
    ]

    worst = effect_summary.loc[
        effect_summary["average_change"].idxmin()
    ]

    insights.append(
        f"Top-performing effect: {biggest['effect_name']} ({biggest['average_change']:.2f}keys)."
    )

    insights.append(
        f"Weakest effect: {worst['effect_name']} ({worst['average_change']:.2f}keys)."
    )

    return insights