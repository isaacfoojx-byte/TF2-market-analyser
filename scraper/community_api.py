from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd

from processing.community_prices import clean_community_prices

from .community_spreadsheet import CommunityScrapeResult, save_snapshot
from .scraping import PRICES_URL, execute_request, key_price_from_payload


QUALITY_NAMES = {
    0: "Normal",
    1: "Genuine",
    3: "Vintage",
    6: "Unique",
    7: "Community",
    8: "Valve",
    9: "Self-Made",
    11: "Strange",
    13: "Haunted",
    14: "Collector's",
    15: "Decorated Weapon",
}
UNUSUAL_QUALITY_ID = 5


def mapping_items(value: Any):
    if isinstance(value, dict):
        return value.items()
    if isinstance(value, list):
        return ((str(index), entry) for index, entry in enumerate(value))
    return ()


def source_price(entry: dict[str, Any]) -> tuple[float, float, str]:
    unit = str(entry.get("currency", "")).strip().lower()
    if unit == "metal":
        unit = "ref"
    if unit not in {"ref", "keys"}:
        raise ValueError(f"Unsupported community price unit: {unit!r}")

    low = entry.get("value")
    high = entry.get("value_high", low)
    if low is None:
        raise ValueError("Community API price has no value")

    low_value = float(low)
    high_value = float(high if high is not None else low)
    if low_value <= 0 or high_value <= 0:
        raise ValueError("Community API price must be positive")
    return min(low_value, high_value), max(low_value, high_value), unit


def price_text(low: float, high: float, unit: str) -> str:
    label = "keys" if unit == "keys" else "ref"
    if abs(low - high) < 1e-9:
        return f"{low:g} {label}"
    return f"{low:g}–{high:g} {label}"


def stats_url(
    item_name: str,
    quality: str,
    craftable: bool,
    priceindex: str,
) -> str:
    craftability = "Craftable" if craftable else "Non-Craftable"
    base = (
        f"https://backpack.tf/stats/{quote(quality, safe='')}/"
        f"{quote(item_name, safe='')}/Tradable/{craftability}"
    )
    return base if priceindex == "0" else f"{base}/{quote(priceindex, safe='')}"


def build_community_rows(
    payload: dict[str, Any],
    scraped_at: datetime | None = None,
) -> pd.DataFrame:
    timestamp = (scraped_at or datetime.now()).isoformat(timespec="seconds")
    key_price_ref = key_price_from_payload(payload)
    records: list[dict[str, Any]] = []

    for item_name, item in mapping_items(payload.get("items", {})):
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("item_type", item.get("type", "")))

        for quality_key, quality_prices in mapping_items(item.get("prices", {})):
            try:
                quality_id = int(quality_key)
            except (TypeError, ValueError):
                continue
            if quality_id == UNUSUAL_QUALITY_ID or not isinstance(quality_prices, dict):
                continue

            quality = QUALITY_NAMES.get(quality_id, f"Quality {quality_id}")
            tradable = quality_prices.get("Tradable", {})
            if not isinstance(tradable, dict):
                continue

            for craftability, craftable in (("Craftable", True), ("Non-Craftable", False)):
                indexed_prices = tradable.get(craftability, {})
                for priceindex, entry in mapping_items(indexed_prices):
                    if not isinstance(entry, dict):
                        continue
                    try:
                        low, high, unit = source_price(entry)
                    except (TypeError, ValueError):
                        continue

                    midpoint = (low + high) / 2
                    price_ref = midpoint * key_price_ref if unit == "keys" else midpoint
                    indexed_item_name = (
                        str(item_name)
                        if str(priceindex) == "0"
                        else f"{item_name} #{priceindex}"
                    )
                    records.append(
                        {
                            "scrape_timestamp": timestamp,
                            "source_url": PRICES_URL,
                            "item_name": indexed_item_name,
                            "item_type": item_type,
                            "quality": quality,
                            "craftable": craftable,
                            "price_ref": price_ref,
                            "price_text": price_text(low, high, unit),
                            "usd_price": None,
                            "stats_url": stats_url(
                                str(item_name),
                                quality,
                                craftable,
                                str(priceindex),
                            ),
                            "key_price_ref": key_price_ref,
                        }
                    )

    return pd.DataFrame.from_records(records)


def run_scraper(
    output_dir: str | Path | None = None,
    scraped_at: datetime | None = None,
    api_key: str | None = None,
) -> CommunityScrapeResult:
    capture_time = scraped_at or datetime.now()
    resolved_api_key = api_key or os.environ.get("BACKPACK_TF_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("Missing required environment variable: BACKPACK_TF_API_KEY")
    payload = execute_request(resolved_api_key)
    rows = build_community_rows(payload, capture_time)
    if rows.empty:
        raise ValueError("The backpack.tf API returned no non-Unusual price rows")

    raw_file = save_snapshot(rows, output_dir=output_dir, scraped_at=capture_time)
    cleaned, processed_file = clean_community_prices(raw_file)
    print(f"Saved {len(rows):,} raw non-Unusual price rows to {raw_file}")
    print(f"Saved {len(cleaned):,} cleaned non-Unusual price rows to {processed_file}")
    return CommunityScrapeResult(raw_file, processed_file, len(cleaned))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    run_scraper(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
