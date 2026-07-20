from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://backpack.tf/stats/Unique/Mann%20Co.%20Supply%20Crate%20Key/Tradable/Craftable"


def get_key_market(driver):

    driver.get(URL)

    WebDriverWait(driver, 10).until(
        lambda d: "Just a moment" not in d.title
    )

    soup = BeautifulSoup(driver.page_source, "html.parser")

    items = soup.find_all("div", class_="item")

    lowest_sell = None
    highest_buy = None

    official_low = None
    official_high = None

    for item in items:

        intent = item.get("data-listing_intent")
        listing_price = item.get("data-listing_price")

        if listing_price is None:
            continue

        listing_price = float(listing_price.replace(" ref", ""))

        # Only need to read this once
        if official_low is None:

            official = item.get("data-p_bptf")   # "57–57.44 ref"

            if official:
                official = official.replace(" ref", "")
                low, high = official.split("–")
                official_low = float(low)
                official_high = float(high)

        if intent == "sell" and lowest_sell is None:
            lowest_sell = listing_price

        elif intent == "buy" and highest_buy is None:
            highest_buy = listing_price

        if lowest_sell is not None and highest_buy is not None:
            break

    return {
        "lowest_sell": lowest_sell,
        "highest_buy": highest_buy,
        "mid_price": (lowest_sell + highest_buy) / 2,
        "official_low": official_low,
        "official_high": official_high,
        "official_mid": (official_low + official_high) / 2
    }
