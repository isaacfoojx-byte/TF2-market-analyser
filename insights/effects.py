import pandas as pd

from .common import missing_columns, unavailable_insight


def generate_effect_insights(
    effect_summary: pd.DataFrame,
) -> list[str]:

    required = {"effect_name", "average_change"}
    missing = missing_columns(effect_summary, required)

    if missing:
        return unavailable_insight(
            "effect",
            f"Missing required data: {', '.join(missing)}.",
        )

    usable_effects = effect_summary.dropna(
        subset=["effect_name", "average_change"]
    )

    if usable_effects.empty:
        return unavailable_insight(
            "effect",
            "Collect another priced market snapshot and try again.",
        )

    biggest = usable_effects.loc[
        usable_effects["average_change"].idxmax()
    ]

    worst = usable_effects.loc[
        usable_effects["average_change"].idxmin()
    ]

    # average_change is currently calculated from price_change, in keys.
    return [
        f"Top-performing effect: {biggest['effect_name']} "
        f"({biggest['average_change']:+.2f} keys on average).",
        f"Weakest effect: {worst['effect_name']} "
        f"({worst['average_change']:+.2f} keys on average).",
    ]
