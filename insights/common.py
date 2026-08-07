import pandas as pd


def percentage(part: float, whole: float) -> float:
    """Return percentage safely."""

    if whole == 0:
        return 0.0

    return (part / whole) * 100


def missing_columns(
    dataframe: pd.DataFrame | None,
    required: set[str],
) -> list[str]:
    """Return required columns that are absent from a dataframe."""

    if dataframe is None:
        return sorted(required)

    return sorted(required.difference(dataframe.columns))


def unavailable_insight(
    subject: str,
    reason: str | None = None,
) -> list[str]:
    """Return a consistent, user-facing message for unavailable insights."""

    message = f"No {subject} insights are available yet."

    if reason:
        message = f"{message} {reason}"

    return [message]


def assess_spotlight(
    comparison: pd.DataFrame,
    entity_column: str,
    entity_name: str,
    represented_markets: int,
    minimum_markets: int,
    average_change: float,
) -> dict:
    """Return confidence, risk, and an explanation for a spotlight candidate."""

    confidence = (
        "High" if represented_markets >= 100
        else "Medium" if represented_markets >= 25
        else "Low"
    )
    assessment = {
        "confidence": confidence,
        "risk_level": "Low",
        "risk_reasons": [],
        "explanation": (
            f"Selected for the highest average price change ({average_change:+.2f} keys) "
            f"among entries with at least {minimum_markets} represented markets."
        ),
    }

    if comparison is None or entity_column not in comparison.columns:
        assessment["risk_level"] = "High"
        assessment["risk_reasons"].append(
            "No comparison data is available to validate this signal."
        )
        return assessment

    entity_rows = comparison.loc[
        comparison[entity_column].eq(entity_name)
    ].copy()

    if represented_markets < 25:
        assessment["risk_reasons"].append(
            "Limited market support makes the signal less reliable."
        )

    if "percent_change" not in entity_rows.columns:
        assessment["risk_reasons"].append(
            "Percentage price movement is unavailable for this signal."
        )
    else:
        percent_changes = pd.to_numeric(
            entity_rows["percent_change"],
            errors="coerce",
        ).dropna()

        if len(percent_changes) < 5:
            assessment["risk_reasons"].append(
                "Too few comparable price movements are available to assess stability."
            )
        else:
            median_absolute_change = float(percent_changes.abs().median())
            volatility = float(percent_changes.std(ddof=0))

            if median_absolute_change >= 25:
                assessment["risk_reasons"].append(
                    "Typical price movement is large, so this may be a short-term swing."
                )

            if volatility >= 25:
                assessment["risk_reasons"].append(
                    "Price movements vary widely across represented markets."
                )

    if "listing_change" in entity_rows.columns:
        listing_changes = pd.to_numeric(
            entity_rows["listing_change"],
            errors="coerce",
        ).dropna()

        if not listing_changes.empty and listing_changes.sum() > 0:
            assessment["risk_reasons"].append(
                "Listing supply increased across the represented markets."
            )

    high_risk = (
        represented_markets < 5
        or any(
            "unavailable" in reason.lower()
            or "too few" in reason.lower()
            or "vary widely" in reason.lower()
            for reason in assessment["risk_reasons"]
        )
    )

    if high_risk:
        assessment["risk_level"] = "High"
    elif assessment["risk_reasons"]:
        assessment["risk_level"] = "Medium"

    return assessment


def build_entity_story_cards(
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
    entity_column: str,
) -> list[dict]:
    """Translate an effect/item summary into three player-friendly cards."""

    required = {entity_column, "average_change", "unusuals"}
    if summary.empty or not required.issubset(summary.columns):
        return []

    usable = summary.dropna(subset=list(required)).copy()
    if usable.empty:
        return []

    # Prefer well-supported entries, but do not hide the page when a smaller
    # dataset has not reached the normal confidence threshold yet.
    supported = usable.loc[usable["unusuals"] >= 25]
    candidates = supported if not supported.empty else usable
    minimum_markets = 25 if not supported.empty else 1

    strongest = candidates.loc[candidates["average_change"].idxmax()]
    most_represented = candidates.loc[candidates["unusuals"].idxmax()]
    weakest = candidates.loc[candidates["average_change"].idxmin()]

    def card_for(row: pd.Series, category: str, headline: str, reason: str) -> dict:
        assessment = assess_spotlight(
            comparison,
            entity_column=entity_column,
            entity_name=row[entity_column],
            represented_markets=int(row["unusuals"]),
            minimum_markets=minimum_markets,
            average_change=float(row["average_change"]),
        )
        assessment["explanation"] = reason

        return {
            "category": category,
            "name": row[entity_column],
            "headline": headline,
            "confidence": assessment["confidence"],
            "risk": assessment["risk_level"],
            "why": assessment["explanation"],
            "risk_reasons": assessment["risk_reasons"],
        }

    strongest_change = float(strongest["average_change"])
    if strongest_change > 0:
        strongest_headline = f"Up about {strongest_change:.2f} keys on average"
        strongest_category = "Gaining attention"
    else:
        strongest_headline = f"Holding up best at {strongest_change:+.2f} keys"
        strongest_category = "Holding up best"

    weakest_change = float(weakest["average_change"])
    weakest_headline = (
        f"Down about {abs(weakest_change):.2f} keys on average"
        if weakest_change < 0
        else f"Up only {weakest_change:.2f} keys on average"
    )

    return [
        card_for(
            strongest,
            strongest_category,
            strongest_headline,
            "Chosen because it has the strongest average price movement among "
            f"entries supported by at least {minimum_markets} markets.",
        ),
        card_for(
            most_represented,
            "Most represented",
            f"Seen across {int(most_represented['unusuals']):,} market variants",
            "Chosen because it appears in the largest number of tracked markets.",
        ),
        card_for(
            weakest,
            "Worth watching",
            weakest_headline,
            "Chosen because it has the weakest average price movement among "
            f"entries supported by at least {minimum_markets} markets.",
        ),
    ]


def format_direction(change: float) -> str:
    """Return a readable direction."""

    if change > 0:
        return "increased"

    if change < 0:
        return "decreased"

    return "remained unchanged"
