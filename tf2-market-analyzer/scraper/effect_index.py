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
            "effect_id": effect.get("data-effect_id"),
            "effect_name": effect.get("data-effect_name")
        })

    

    seen = set()
    unique_effects = []

    for effect in effects:

        if effect["effect_name"] not in seen:
            unique_effects.append(effect)
            seen.add(effect["effect_name"])

    return unique_effects