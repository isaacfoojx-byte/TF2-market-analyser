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


def format_direction(change: float) -> str:
    """Return a readable direction."""

    if change > 0:
        return "increased"

    if change < 0:
        return "decreased"

    return "remained unchanged"
