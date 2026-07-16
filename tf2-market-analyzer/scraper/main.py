from browser import get_driver
from effect_details import scrape_effect
from csv_utils import save_csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

driver = get_driver()

effects = scrape_effect(driver, "Nebula")

master_dataset = []

for effect in effects:

    print(f"Scraping {effect['effect_name']}...")

    hats = scrape_effect(
        driver,
        effect["effect_name"]
    )

    master_dataset.extend(hats)

save_csv(
    effects,
    BASE_DIR / "data" / "Nebula.csv"
)

print("Done!")

