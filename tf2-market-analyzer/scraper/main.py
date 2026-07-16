from browser import get_driver
from effect_details import scrape_effect
from csv_utils import save_csv

driver = get_driver()

effects = scrape_effect(driver, "Nebula")

save_csv(effects, "data/Nebula.csv")

print("Done!")