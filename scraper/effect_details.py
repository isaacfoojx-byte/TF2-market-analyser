from bs4 import BeautifulSoup
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

def scrape_effect(driver, effect_name):

    driver.get(f"https://backpack.tf/effect/{effect_name}")

    WebDriverWait(driver, 10).until(
        lambda d: "Just a moment" not in d.title
    )

    html = driver.page_source # Get the HTML source of the current page

    soup = BeautifulSoup(html, "html.parser")  # Parse the HTML with BeautifulSoup

    elements = soup.find_all(
        "li",
        attrs={"data-effect_name": True}
    )

    effects = []

    

    for effect in elements:
        effects.append({
            "effect_id": effect.get("data-effect_id"),
            "effect_name": effect.get("data-effect_name"),
            "item_name": effect.get("data-base_name"),
            "price_ref": effect.get("data-price"),
            "exist": effect.get("data-exist"),
            "slot": effect.get("data-slot"),
            "summary": effect.get("data-summary"),
            "defindex": effect.get("data-defindex"),
        })

    return effects




