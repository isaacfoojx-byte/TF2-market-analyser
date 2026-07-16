from browser import get_driver
from effect_details import scrape_effect
from csv_utils import save_csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

driver = get_driver()

effects = scrape_effect(driver, "Nebula")

save_csv(
    effects,
    BASE_DIR / "data" / "Nebula.csv"
)

print("Done!")

