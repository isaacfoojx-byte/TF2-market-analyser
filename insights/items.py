import pandas as pd

from .common import missing_columns, unavailable_insight


def generate_item_insights(
    item_summary: pd.DataFrame,
) -> list[str]:

    required = {"item_name", "average_change"}
    missing = missing_columns(item_summary, required)

    if missing:
        return unavailable_insight(
            "item",
            f"Missing required data: {', '.join(missing)}.",
        )

    usable_items = item_summary.dropna(
        subset=["item_name", "average_change"]
    )

    if usable_items.empty:
        return unavailable_insight(
            "item",
            "Collect another priced market snapshot and try again.",
        )

    biggest = usable_items.loc[
        usable_items["average_change"].idxmax()
    ]

    worst = usable_items.loc[
        usable_items["average_change"].idxmin()
    ]

    # average_change is currently calculated from price_change, in keys.
    return [
        f"Best-performing item: {biggest['item_name']} "
        f"({biggest['average_change']:+.2f} keys on average).",
        f"Largest decline: {worst['item_name']} "
        f"({worst['average_change']:+.2f} keys on average).",
    ]
