import pandas as pd


def percentage(part: int, whole: int) -> float:
    """Return percentage safely."""

    if whole == 0:
        return 0.0

    return (part / whole) * 100


def format_direction(change: float) -> str:
    """Return a readable direction."""

    if change > 0:
        return "increased"

    if change < 0:
        return "decreased"

    return "remained unchanged"