from pydoc import html

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_all_effects(driver):

    driver.get("https://backpack.tf/effects")

    html = driver.page_source

    

    print("Saved!")

    print(driver.title)

    WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-effect_name]"))
)

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