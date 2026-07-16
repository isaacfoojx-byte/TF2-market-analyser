from bs4 import BeautifulSoup
import time

def scrape_effect(driver, effect_name):

    driver.get(f"https://backpack.tf/effect/{effect_name}")

    time.sleep(2)

    html = driver.page_source # Get the HTML source of the current page

    soup = BeautifulSoup(html, "html.parser")  # Parse the HTML with BeautifulSoup

    elements = soup.find_all(attrs={"data-effect_name": True})

    effects = []

    for effect in elements:
        effects.append({
                "effect_id": effect["data-effect_id"],
                "effect_name": effect["data-effect_name"],
                "item_name": effect["data-base_name"],
                "price_ref": effect["data-price"],
                "exist": effect["data-exist"],
                "slot": effect["data-slot"],
                "summary": effect["data-summary"],
                "defindex": effect["data-defindex"]
            })

    return effects




