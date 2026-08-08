"""Fetch one approximate Unusual existence count on demand from backpack.tf."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import quote

from bs4 import BeautifulSoup
import requests


UNUSUAL_ITEM_URL = "https://backpack.tf/unusual/{item_name}?view=list"
REQUEST_TIMEOUT_SECONDS = 15
REQUEST_HEADERS = {
    "User-Agent": "TFAnalytics/1.0 (on-demand Unusual existence lookup)",
}
COUNT_PATTERN = re.compile(r"~\s*(\d{1,3}(?:,\d{3})*)")


class ExistenceLookupError(RuntimeError):
    """Raised when backpack.tf cannot provide one requested count."""


def normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def unusual_item_url(item_name: str) -> str:
    return UNUSUAL_ITEM_URL.format(item_name=quote(item_name, safe=""))


def _row_effect_names(row) -> set[str]:
    """Collect likely effect labels from a backpack.tf price-table row."""

    names = set()
    for node in row.select("[data-effect-name], [data-effect_name], a, img[alt]"):
        for value in (
            node.get("data-effect-name"),
            node.get("data-effect_name"),
            node.get("alt"),
            node.get_text(" ", strip=True),
        ):
            if value:
                names.add(normalise_text(str(value)))

    cells = row.select("td")
    if cells:
        names.add(normalise_text(cells[0].get_text(" ", strip=True)))
    return names


def parse_existence_count(html: str, effect_name: str) -> int | None:
    """Extract one approximate count from the selected effect's table row."""

    target_effect = normalise_text(effect_name)
    soup = BeautifulSoup(html, "html.parser")

    for row in soup.select("tr"):
        if target_effect not in _row_effect_names(row):
            continue

        # backpack.tf renders the approximate count in the final column. Looking
        # for a tilde avoids confusing it with a suggested price in earlier cells.
        cells = row.select("td")
        for cell in reversed(cells):
            match = COUNT_PATTERN.search(cell.get_text(" ", strip=True))
            if match:
                return int(match.group(1).replace(",", ""))

    return None


def fetch_existence_count(
    item_name: str,
    effect_name: str,
    timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> dict[str, str | int]:
    """Fetch the current approximate count for one Unusual market.

    This intentionally makes one item-page request only. The result is returned
    to the caller rather than being added to a raw or processed market snapshot.
    """

    url = unusual_item_url(item_name)
    client = session or requests.Session()
    try:
        response = client.get(url, headers=REQUEST_HEADERS, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as error:
        raise ExistenceLookupError(
            "backpack.tf could not be reached for this existence lookup."
        ) from error

    count = parse_existence_count(response.text, effect_name)
    if count is None:
        raise ExistenceLookupError(
            "backpack.tf did not show an existence estimate for this effect."
        )

    return {
        "count": count,
        "source_url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
