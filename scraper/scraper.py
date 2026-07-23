from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from processing.clean_data import clean_data
from processing.key_price import get_key_market

from .browser import get_driver
from .csv_utils import save_csv
from .effect_details import scrape_effect
from .effect_index import get_all_effects


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REQUEST_DELAY_SECONDS = 0.05


@dataclass(frozen=True)
class ScrapeResult:
    raw_csv: Path
    processed_csv: Path
    row_count: int


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


def run_scraper(
    debug_port: int,
    output_dir: str | Path | None = None,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    scrape_datetime: datetime | None = None,
) -> ScrapeResult:
    started_at = scrape_datetime or datetime.now()
    scrape_timestamp = started_at.isoformat(timespec="seconds")
    raw_csv, processed_csv = build_output_paths(output_dir, started_at)

    driver = get_driver(debug_port)
    master_dataset: list[dict] = []
    current_key_price: float | None = None

    try:
        current_key_market = get_key_market(driver)
        print("Current key market:")
        print(current_key_market)
        current_key_price = current_key_market["mid_price"]

        effects = get_all_effects(driver)

        for index, effect in enumerate(effects, start=1):
            try:
                hats = scrape_effect(
                    driver,
                    effect["effect_name"],
                    scrape_timestamp,
                )
                master_dataset.extend(hats)

                # Keep a recoverable checkpoint after every completed effect.
                save_csv(master_dataset, raw_csv)

                print(
                    f"[{index}/{len(effects)}] "
                    f"{effect['effect_name']} "
                    f"| {len(hats)} hats "
                    f"| Total rows: {len(master_dataset)}"
                )
            except Exception as error:
                print(f"Failed: {effect['effect_name']} ({error})")

            time.sleep(request_delay_seconds)
    finally:
        driver.quit()

    if not master_dataset or current_key_price is None:
        raise RuntimeError("Scraping completed without any rows to clean.")

    clean_data(raw_csv, processed_csv, current_key_price)
    print("Done!")

    return ScrapeResult(
        raw_csv=raw_csv,
        processed_csv=processed_csv,
        row_count=len(master_dataset),
    )


if __name__ == "__main__":
    run_scraper()
