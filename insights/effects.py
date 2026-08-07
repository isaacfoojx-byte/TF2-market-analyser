import pandas as pd

from .common import build_entity_story_cards, missing_columns, unavailable_insight


def generate_effect_insights(effect_summary: pd.DataFrame) -> list[str]:
    """Return safe narrative summaries for the full effect dataset."""

    required = {"effect_name", "average_change"}
    missing = missing_columns(effect_summary, required)
    if missing:
        return unavailable_insight("effect", f"Missing data: {', '.join(missing)}.")

    usable_effects = effect_summary.dropna(subset=["effect_name", "average_change"])
    if usable_effects.empty:
        return unavailable_insight("effect", "Collect another priced market snapshot and try again.")

    biggest = usable_effects.loc[usable_effects["average_change"].idxmax()]
    weakest = usable_effects.loc[usable_effects["average_change"].idxmin()]

    return [
        f"Strongest effect: {biggest['effect_name']} "
        f"({biggest['average_change']:+.2f} keys on average).",
        f"Weakest effect: {weakest['effect_name']} "
        f"({weakest['average_change']:+.2f} keys on average).",
    ]


def build_effect_cards(
    effect_summary: pd.DataFrame,
    comparison: pd.DataFrame,
) -> list[dict]:
    """Build player-facing effect cards from the underlying summary data."""

    return build_entity_story_cards(effect_summary, comparison, "effect_name")
