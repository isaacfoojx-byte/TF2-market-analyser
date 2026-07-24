import os
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://backpack.tf/stats/Unique/Mann%20Co.%20Supply%20Crate%20Key/Tradable/Craftable"
MAX_ATTEMPTS = 3
WAIT_SECONDS = 60


def save_diagnostics(driver, attempt):
    output_dir = Path(os.environ.get("OUTPUT_DIR", "data"))
    diagnostics_dir = output_dir / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    try:
        driver.save_screenshot(
            str(diagnostics_dir / f"key-price-attempt-{attempt}.png")
        )
        (diagnostics_dir / f"key-price-attempt-{attempt}.html").write_text(
            driver.page_source,
            encoding="utf-8",
        )
    except Exception as error:
        print(f"Could not save key-price diagnostics: {error}")


def parse_key_market(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    items = soup.select("div.item[data-listing_price]")
    lowest_sell = None
    highest_buy = None
    official_low = None
    official_high = None

    for item in items:
        intent = item.get("data-listing_intent")
        listing_price = item.get("data-listing_price")

        if not listing_price:
            continue

        listing_numbers = re.findall(r"\d+(?:\.\d+)?", listing_price)
        if not listing_numbers:
            continue
        price = float(listing_numbers[0])

        if official_low is None:
            official = item.get("data-p_bptf", "")
            official_numbers = re.findall(r"\d+(?:\.\d+)?", official)
            if len(official_numbers) >= 2:
                official_low = float(official_numbers[0])
                official_high = float(official_numbers[1])

        if intent == "sell" and lowest_sell is None:
            lowest_sell = price
        elif intent == "buy" and highest_buy is None:
            highest_buy = price

        if (
            lowest_sell is not None
            and highest_buy is not None
            and official_low is not None
            and official_high is not None
        ):
            break

    if lowest_sell is None or highest_buy is None:
        raise ValueError("Key-price listings did not contain both buy and sell prices")

    result = {
        "lowest_sell": lowest_sell,
        "highest_buy": highest_buy,
        "mid_price": (lowest_sell + highest_buy) / 2,
        "official_low": official_low,
        "official_high": official_high,
        "official_mid": None,
    }

    if official_low is not None and official_high is not None:
        result["official_mid"] = (official_low + official_high) / 2

    return result


def get_key_market(driver):
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Loading key-price market, attempt {attempt}/{MAX_ATTEMPTS}")

        try:
            driver.get(URL)
            WebDriverWait(driver, WAIT_SECONDS).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.item[data-listing_price]")
                )
            )
            result = parse_key_market(driver.page_source)
            print(f"Key-price market loaded on attempt {attempt}")
            return result
        except (TimeoutException, ValueError) as error:
            last_error = error
            save_diagnostics(driver, attempt)
            title = ""
            current_url = URL
            try:
                title = driver.title
                current_url = driver.current_url
            except Exception:
                pass
            print(
                f"Key-price attempt {attempt} failed "
                f"| title={title!r} | url={current_url}"
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(
        f"Key-price market failed after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error
