from collections.abc import Mapping

import pandas as pd

from .common import (
    missing_columns,
    percentage,
    unavailable_insight,
)


PRICE_INCREASED = "Price Increased"
PRICE_DECREASED = "Price Decreased"


def calculate_market_sentiment(comparison: pd.DataFrame) -> dict:
    """Score comparable markets using price breadth and median movement.

    The result describes the available snapshot data; it is not an investment
    recommendation. New and removed listings are excluded because they do not
    have a price in both snapshots.
    """

    required = {"status", "price_change"}
    missing = missing_columns(comparison, required)

    if missing:
        return {
            "score": None,
            "label": "Insufficient data",
            "confidence": "Low",
            "reason": f"Missing required data: {', '.join(missing)}.",
        }

    price_rows = comparison.loc[
        comparison["status"].isin([PRICE_INCREASED, PRICE_DECREASED]),
        ["status", "price_change"],
    ].copy()
    price_rows["price_change"] = pd.to_numeric(
        price_rows["price_change"],
        errors="coerce",
    )
    price_rows = price_rows.dropna(subset=["price_change"])

    if price_rows.empty:
        return {
            "score": None,
            "label": "Insufficient data",
            "confidence": "Low",
            "reason": "No comparable priced markets were found.",
        }

    rising = int((price_rows["status"] == PRICE_INCREASED).sum())
    falling = int((price_rows["status"] == PRICE_DECREASED).sum())
    comparable_markets = len(price_rows)
    breadth = percentage(rising, comparable_markets)

    # Breadth drives the score. Median movement has only a small influence so
    # an unusually expensive listing cannot dominate market sentiment.
    median_change = float(price_rows["price_change"].median())
    movement_adjustment = max(-5.0, min(5.0, median_change))
    score = round(max(0.0, min(100.0, breadth + movement_adjustment)))

    if score >= 60:
        label = "Bullish"
    elif score <= 40:
        label = "Bearish"
    else:
        label = "Neutral"

    confidence = (
        "High" if comparable_markets >= 100
        else "Medium" if comparable_markets >= 25
        else "Low"
    )

    return {
        "score": score,
        "label": label,
        "confidence": confidence,
        "rising_markets": rising,
        "falling_markets": falling,
        "comparable_markets": comparable_markets,
        "breadth_percent": round(breadth, 1),
        "median_change_keys": round(median_change, 2),
        "reason": (
            f"{breadth:.1f}% of comparable markets rose in price; "
            f"the median change was {median_change:+.2f} keys."
        ),
    }


def detect_market_risks(comparison: pd.DataFrame) -> list[str]:
    """Return high-level data-quality and volatility warnings."""

    sentiment = calculate_market_sentiment(comparison)

    if sentiment["score"] is None:
        return [sentiment["reason"]]

    risks: list[str] = []

    if sentiment["confidence"] == "Low":
        risks.append(
            "Low confidence: fewer than 25 comparable priced markets are available."
        )

    falling_share = percentage(
        sentiment["falling_markets"],
        sentiment["comparable_markets"],
    )
    if falling_share >= 70:
        risks.append(
            f"Broad market decline: {falling_share:.1f}% of comparable markets "
            "fell in price."
        )

    if "percent_change" in comparison.columns:
        percent_changes = pd.to_numeric(
            comparison["percent_change"],
            errors="coerce",
        ).dropna()

        if not percent_changes.empty:
            large_moves = (percent_changes.abs() >= 25).sum()
            large_move_share = percentage(large_moves, len(percent_changes))

            if large_move_share >= 10:
                risks.append(
                    f"High volatility: {large_move_share:.1f}% of comparable markets "
                    "moved by at least 25%."
                )

    if "listing_change" in comparison.columns:
        listing_changes = pd.to_numeric(
            comparison["listing_change"],
            errors="coerce",
        ).dropna()

        if not listing_changes.empty and listing_changes.sum() > 0:
            risks.append(
                "Listing supply increased overall, which can put downward pressure on prices."
            )

    return risks or ["No broad market risk flags were triggered in this comparison."]


def find_opportunities(
    comparison: pd.DataFrame,
    minimum_listings: int = 3,
    limit: int = 10,
) -> pd.DataFrame:
    """Rank liquid, rising markets with stable or falling listing supply.

    This is a screening tool, not a prediction or investment recommendation.
    """

    required = {
        "effect_name",
        "item_name",
        "status",
        "percent_change",
        "listing_change",
        "listings_new",
    }
    missing = missing_columns(comparison, required)

    if missing:
        return pd.DataFrame()

    candidates = comparison.loc[
        comparison["status"].eq(PRICE_INCREASED),
        list(required),
    ].copy()

    for column in ("percent_change", "listing_change", "listings_new"):
        candidates[column] = pd.to_numeric(candidates[column], errors="coerce")

    candidates = candidates.dropna(
        subset=["percent_change", "listing_change", "listings_new"]
    )
    candidates = candidates.loc[
        (candidates["percent_change"] > 0)
        & (candidates["listing_change"] <= 0)
        & (candidates["listings_new"] >= minimum_listings)
    ]

    if candidates.empty:
        return candidates

    # Cap momentum so an extreme one-snapshot movement cannot receive an
    # unbounded score.
    candidates["opportunity_score"] = (
        candidates["percent_change"].clip(upper=50)
        + candidates["listings_new"].clip(upper=20)
    ).round(1)

    return candidates.sort_values(
        ["opportunity_score", "listings_new"],
        ascending=False,
    ).head(limit)


def generate_market_insights(
    comparison: pd.DataFrame,
    summary: Mapping[str, int | float],
) -> list[str]:
    """Generate concise, defensive insight text for the latest comparison."""

    required_summary_fields = {
        "total_unusuals",
        "price_up",
        "price_down",
        "unchanged",
    }
    missing = sorted(required_summary_fields.difference(summary.keys()))

    if missing:
        return unavailable_insight(
            "market",
            f"Missing required summary data: {', '.join(missing)}.",
        )

    total = int(summary["total_unusuals"])

    if total <= 0:
        return unavailable_insight(
            "market",
            "No comparable markets were found.",
        )

    gainers = int(summary["price_up"])
    losers = int(summary["price_down"])
    unchanged = int(summary["unchanged"])

    insights = [
        f"{percentage(gainers, total):.1f}% of markets increased in price.",
        f"{percentage(losers, total):.1f}% of markets decreased in price.",
        f"{unchanged:,} markets remained unchanged.",
    ]

    sentiment = calculate_market_sentiment(comparison)
    if sentiment["score"] is None:
        insights.append(f"Sentiment unavailable: {sentiment['reason']}")
    else:
        insights.append(
            f"Market sentiment is {sentiment['label'].lower()} "
            f"({sentiment['score']}/100, {sentiment['confidence'].lower()} confidence). "
            f"{sentiment['reason']}"
        )

    risks = detect_market_risks(comparison)
    if risks and not risks[0].startswith("No broad"):
        insights.append(f"Risk flag: {risks[0]}")

    opportunities = find_opportunities(comparison, limit=1)
    if not opportunities.empty:
        top = opportunities.iloc[0]
        insights.append(
            f"Potential opportunity: {top['effect_name']} {top['item_name']} "
            f"rose {top['percent_change']:+.1f}% while listings did not increase."
        )

    return insights
