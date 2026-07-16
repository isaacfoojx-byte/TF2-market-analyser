from bs4 import BeautifulSoup
import time


def get_all_effects(driver):

    driver.get("https://backpack.tf/effects")

    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    effect_boxes = soup.find_all(attrs={"data-effect_name": True})

    effects = []

    for effect in effect_boxes:

        effects.append({
            "effect_id": effect["data-effect_id"],
            "effect_name": effect["data-effect_name"]
        })

    return effects