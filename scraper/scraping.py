from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from analytics.metadata import save_metadata
from processing.clean_data import clean_data

from .csv_utils import save_csv


BASE_DIR = Path(__file__).resolve().parent.parent
PRICES_URL = "https://backpack.tf/api/IGetPrices/v4"
MAX_ATTEMPTS = 5
REQUEST_TIMEOUT_SECONDS = 90


@dataclass(frozen=True)
class ScrapeResult:
    raw_csv: Path
    processed_csv: Path
    row_count: int


@dataclass(frozen=True)
class Catalog:
    effect_names: dict[int, str]
    item_details: dict[tuple[str, int], tuple[str, str]]
    item_defaults: dict[str, tuple[str, str, int]]


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_output_paths(
    output_dir: str | Path | None = None,
    scrape_datetime: datetime | None = None,
) -> tuple[Path, Path]:
    timestamp = (scrape_datetime or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    configured_dir = output_dir or os.environ.get("OUTPUT_DIR")
    data_dir = Path(configured_dir) if configured_dir else BASE_DIR / "data"
    return (
        data_dir / "raw" / f"unusuals_{timestamp}.csv",
        data_dir / "processed" / "archive" / f"cleaned_{timestamp}.csv",
    )


def latest_catalog_csv() -> Path | None:
    candidates = sorted((BASE_DIR / "data" / "raw").glob("unusuals_*.csv"))
    return candidates[-1] if candidates else None


def load_catalog(path: Path | None = None) -> Catalog:
    source = path or latest_catalog_csv()
    effect_names: dict[int, str] = {}
    item_details: dict[tuple[str, int], tuple[str, str]] = {}
    item_defaults: dict[str, tuple[str, str, int]] = {}

    if source is None:
        return Catalog(effect_names, item_details, item_defaults)

    with source.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            try:
                effect_id = int(row.get("effect_id", ""))
                defindex = int(row.get("defindex", ""))
            except ValueError:
                continue

            effect_name = row.get("effect_name", "").strip()
            item_name = row.get("item_name", "").strip()
            slot = row.get("slot", "").strip()
            summary = row.get("summary", "").strip()

            if effect_name:
                effect_names[effect_id] = effect_name
            if item_name:
                item_details[(item_name, defindex)] = (slot, summary)
                item_defaults.setdefault(item_name, (slot, summary, defindex))

    return Catalog(effect_names, item_details, item_defaults)


def execute_request(api_key: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "TF2-market-analyser/1.0",
        "X-App-Context": "440",
    }
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                PRICES_URL,
                params={"key": api_key.strip(), "raw": 2},
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 30)
                print(
                    f"Pricing API attempt {attempt}/{MAX_ATTEMPTS} returned "
                    f"HTTP {response.status_code}; retrying in {delay:g} seconds"
                )
                time.sleep(delay)
                continue

            response.raise_for_status()
            body = response.json()
            payload = body.get("response", body)
            if not isinstance(payload, dict):
                raise ValueError("Pricing API returned an invalid response structure")
            if not payload.get("success"):
                message = payload.get("message", "")
                if isinstance(message, list):
                    message = " ".join(str(value) for value in message)
                raise RuntimeError(
                    f"Pricing API rejected the request: {message}"
                )
            return payload
        except RuntimeError:
            raise
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt == MAX_ATTEMPTS:
                break
            delay = min(2**attempt, 30)
            print(
                f"Pricing API attempt {attempt}/{MAX_ATTEMPTS} failed; "
                f"retrying in {delay:g} seconds"
            )
            time.sleep(delay)

    raise RuntimeError(
        f"Pricing API failed after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def get_mapping_value(mapping: Any, key: str) -> Any:
    if isinstance(mapping, dict):
        return mapping.get(key, mapping.get(str(key)))
    if isinstance(mapping, list) and key == "0" and mapping:
        return mapping[0]
    return None


def get_price_entry(
    item: dict[str, Any],
    quality: str,
    priceindex: str,
) -> dict[str, Any]:
    prices = item.get("prices", {})
    quality_prices = get_mapping_value(prices, quality) or {}
    tradable = quality_prices.get("Tradable", {})
    craftable = tradable.get("Craftable", {})
    entry = get_mapping_value(craftable, priceindex)
    return entry if isinstance(entry, dict) else {}


def key_price_from_payload(payload: dict[str, Any]) -> float:
    items = payload.get("items", {})
    key_item = items.get("Mann Co. Supply Crate Key")
    if not isinstance(key_item, dict):
        raise ValueError("Pricing API response does not contain the key item")

    entry = get_price_entry(key_item, "6", "0")
    if not entry:
        raise ValueError("Pricing API response does not contain a craftable key price")

    low = entry.get("value_raw", entry.get("value"))
    high = entry.get("value_raw_high", entry.get("value_high", low))
    if low is None:
        raise ValueError("Pricing API key price has no value")

    return (float(low) + float(high if high is not None else low)) / 2


def price_values(
    entry: dict[str, Any],
    key_price: float,
) -> tuple[float, float, float]:
    currency = str(entry.get("currency", "")).lower()
    low = entry.get("value")
    high = entry.get("value_high", low)
    raw_low = entry.get("value_raw")
    raw_high = entry.get("value_raw_high", raw_low)

    if low is None:
        raise ValueError("Price entry has no value")

    low = float(low)
    high = float(high if high is not None else low)

    if raw_low is not None:
        ref_low = float(raw_low)
        ref_high = float(raw_high if raw_high is not None else raw_low)
    elif currency == "keys":
        ref_low = low * key_price
        ref_high = high * key_price
    elif currency == "metal":
        ref_low = low
        ref_high = high
    else:
        raise ValueError(f"Unsupported pricing currency: {currency!r}")

    if currency == "keys":
        key_low = low
        key_high = high
    else:
        key_low = ref_low / key_price
        key_high = ref_high / key_price

    return (ref_low + ref_high) / 2, key_low, key_high


def format_key_range(low: float, high: float) -> str:
    if abs(low - high) < 1e-9:
        return f"{low:g} keys"
    return f"{low:g}–{high:g} keys"


def select_defindex(item: dict[str, Any], item_name: str, catalog: Catalog) -> int:
    defindices = item.get("defindex", [])
    if isinstance(defindices, dict):
        defindices = list(defindices.values())
    for value in defindices:
        try:
            defindex = int(value)
        except (TypeError, ValueError):
            continue
        if (item_name, defindex) in catalog.item_details:
            return defindex

    if defindices:
        try:
            return int(defindices[0])
        except (TypeError, ValueError):
            pass

    default = catalog.item_defaults.get(item_name)
    return default[2] if default else 0


def build_rows(
    payload: dict[str, Any],
    scrape_timestamp: str,
    catalog: Catalog,
) -> tuple[list[dict[str, Any]], float]:
    key_price = key_price_from_payload(payload)
    rows: list[dict[str, Any]] = []

    for item_name, item in payload.get("items", {}).items():
        if not isinstance(item, dict):
            continue

        quality_prices = get_mapping_value(item.get("prices", {}), "5")
        if not isinstance(quality_prices, dict):
            continue

        craftable = (
            quality_prices.get("Tradable", {}).get("Craftable", {})
        )
        if not isinstance(craftable, dict):
            continue

        defindex = select_defindex(item, item_name, catalog)
        slot, summary = catalog.item_details.get(
            (item_name, defindex),
            catalog.item_defaults.get(item_name, ("", "", defindex))[:2],
        )

        for priceindex, entry in craftable.items():
            if not isinstance(entry, dict):
                continue
            try:
                effect_id = int(priceindex)
                if effect_id <= 0:
                    continue
                ref_price, key_low, key_high = price_values(entry, key_price)
            except (TypeError, ValueError):
                continue

            rows.append(
                {
                    "effect_id": effect_id,
                    "effect_name": catalog.effect_names.get(
                        effect_id,
                        f"Effect {effect_id}",
                    ),
                    "item_name": item_name,
                    "bp_price_ref": round(ref_price, 6),
                    "bp_price_keys": format_key_range(key_low, key_high),
                    "bp_price_all": f"{ref_price:,.2f} ref",
                    "exist": 0,
                    "slot": slot,
                    "summary": summary,
                    "defindex": defindex,
                    "scrape_timestamp": scrape_timestamp,
                }
            )

    if not rows:
        raise RuntimeError("Pricing API returned no craftable unusual prices")

    rows.sort(key=lambda row: (row["effect_id"], row["item_name"]))
    return rows, key_price


def run_scraper(
    output_dir: str | Path | None = None,
    scrape_datetime: datetime | None = None,
    api_key: str | None = None,
    catalog_path: Path | None = None,
) -> ScrapeResult:
    started_at = scrape_datetime or datetime.now()
    started_timer = time.perf_counter()
    scrape_timestamp = started_at.isoformat(timespec="seconds")
    raw_csv, processed_csv = build_output_paths(output_dir, started_at)
    print(f"API scrape started at {started_at.astimezone().isoformat(timespec='seconds')}")

    try:
        payload = execute_request(api_key or required_environment("BACKPACK_TF_API_KEY"))
        rows, key_price = build_rows(
            payload,
            scrape_timestamp,
            load_catalog(catalog_path),
        )
        save_csv(rows, raw_csv)
        clean_data(raw_csv, processed_csv, key_price)
        duration = time.perf_counter() - started_timer
        save_metadata(
            snapshot_timestamp=scrape_timestamp,
            key_price=key_price,
            total_listings=len(rows),
            scrape_duration=round(duration, 2),
            source="backpack_tf_api",
        )
        print(f"API rows written: {len(rows):,}")
        return ScrapeResult(raw_csv, processed_csv, len(rows))
    finally:
        duration = time.perf_counter() - started_timer
        print(
            f"API scrape stopped at "
            f"{datetime.now().astimezone().isoformat(timespec='seconds')}"
        )
        print(f"API scrape elapsed time: {duration:.1f} seconds")


def main() -> None:
    run_scraper()


if __name__ == "__main__":
    main()
