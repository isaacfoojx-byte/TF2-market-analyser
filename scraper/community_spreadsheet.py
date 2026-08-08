"""Capture backpack.tf's community price spreadsheet as timestamped snapshots."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from processing.community_prices import clean_community_prices


SPREADSHEET_URL = "https://backpack.tf/spreadsheet"
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RAW_OUTPUT_DIR = BASE_DIR / "data/community/raw"
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class CommunityScrapeResult:
    """The raw and processed files created by one community guide scrape."""

    raw_csv: Path
    processed_csv: Path
    row_count: int


def parse_usd_price(value: str | None) -> float | None:
    """Convert a tooltip value such as '$0.2066' into a number."""

    if not value:
        return None

    try:
        return float(value.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def parse_community_spreadsheet(
    html: str,
    scraped_at: datetime | None = None,
) -> pd.DataFrame:
    """Parse every non-zero item/quality price from the community spreadsheet."""

    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#pricelist")

    if table is None:
        raise ValueError("Could not find the community price table (#pricelist).")

    headers = [
        header.get_text(" ", strip=True)
        for header in table.select("thead th")
    ]
    if len(headers) < 3:
        raise ValueError("The community price table has no quality columns.")

    qualities = headers[2:]
    timestamp = (scraped_at or datetime.now()).isoformat(timespec="seconds")
    records: list[dict] = []

    for row in table.select("tbody tr"):
        cells = row.select("td")
        if len(cells) < 2:
            continue

        item_name = cells[0].get_text(" ", strip=True)
        item_type = cells[1].get_text(" ", strip=True)
        craftable_value = row.get("data-craftable")
        craftable = (
            True if craftable_value == "1"
            else False if craftable_value == "0"
            else None
        )

        for quality, cell in zip(qualities, cells[2:]):
            try:
                price_ref = float(cell.get("abbr", "0") or 0)
            except ValueError:
                continue

            # Empty quality cells use a zero abbr attribute.
            if price_ref <= 0:
                continue

            price_link = cell.select_one("a")
            stats_url = None
            usd_price = None
            if price_link is not None:
                stats_url = urljoin(SPREADSHEET_URL, price_link.get("href", ""))
                usd_price = parse_usd_price(price_link.get("title"))

            records.append({
                "scrape_timestamp": timestamp,
                "source_url": SPREADSHEET_URL,
                "item_name": item_name,
                "item_type": item_type,
                "quality": quality,
                "craftable": craftable,
                "price_ref": price_ref,
                "price_text": cell.get_text(" ", strip=True),
                "usd_price": usd_price,
                "stats_url": stats_url,
            })

    return pd.DataFrame(records)


def fetch_community_snapshot(
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[str, float]:
    """Fetch the spreadsheet and the live key price in one browser session."""

    return _fetch_with_browser(timeout_seconds)


def fetch_community_spreadsheet(
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Return spreadsheet HTML for callers that only need to parse the table."""

    html, _ = fetch_community_snapshot(timeout_seconds)
    return html


def _fetch_with_browser(timeout_seconds: int) -> tuple[str, float]:
    """Use the project's Chrome session for the guide and its key conversion rate."""

    # Import lazily so parsing and unit tests do not need to launch a browser.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    from . import main as browser_launcher
    from .browser import get_driver
    from processing.key_price import get_key_market

    chrome_process = None
    profile_dir = None
    try:
        chrome_process, profile_dir = browser_launcher.launch_chrome()
        browser_launcher.wait_for_cloudflare_clearance(
            browser_launcher.DEBUG_PORT,
            timeout_seconds=timeout_seconds,
        )

        driver = get_driver(browser_launcher.DEBUG_PORT)
        key_market = get_key_market(driver)
        key_price_ref = float(key_market["mid_price"])
        if key_price_ref <= 0:
            raise ValueError("The captured key price must be greater than zero.")

        driver.get(SPREADSHEET_URL)
        WebDriverWait(driver, timeout_seconds).until(
            lambda active_driver: active_driver.find_elements(By.CSS_SELECTOR, "#pricelist")
        )
        return driver.page_source, key_price_ref
    finally:
        if chrome_process is not None:
            browser_launcher.stop_chrome(chrome_process)
        if profile_dir is not None:
            shutil.rmtree(profile_dir, ignore_errors=True)


def save_snapshot(
    rows: pd.DataFrame,
    output_dir: str | Path | None = None,
    scraped_at: datetime | None = None,
) -> Path:
    """Save one parsed spreadsheet snapshot without overwriting prior history."""

    timestamp = (scraped_at or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    destination = Path(output_dir) if output_dir else DEFAULT_RAW_OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)

    output_file = destination / f"community_prices_{timestamp}.csv"
    rows.to_csv(output_file, index=False)
    return output_file


def run_scraper(
    output_dir: str | Path | None = None,
    scraped_at: datetime | None = None,
) -> CommunityScrapeResult:
    """Fetch, save, and clean one community price-guide snapshot."""

    capture_time = scraped_at or datetime.now()
    html, key_price_ref = fetch_community_snapshot()
    rows = parse_community_spreadsheet(html, scraped_at=capture_time)

    if rows.empty:
        raise ValueError("The community spreadsheet returned no priced item rows.")

    rows["key_price_ref"] = key_price_ref

    raw_file = save_snapshot(
        rows,
        output_dir=output_dir,
        scraped_at=capture_time,
    )
    cleaned, processed_file = clean_community_prices(raw_file)
    print(f"Saved {len(rows):,} raw community price rows to {raw_file}")
    print(f"Saved {len(cleaned):,} cleaned community price rows to {processed_file}")
    return CommunityScrapeResult(
        raw_csv=raw_file,
        processed_csv=processed_file,
        row_count=len(cleaned),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape and clean backpack.tf community price-guide data."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Directory for the raw snapshot. The cleaned snapshot is saved in "
            "a sibling processed directory. Defaults to data/community/raw."
        ),
    )
    args = parser.parse_args()
    run_scraper(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
