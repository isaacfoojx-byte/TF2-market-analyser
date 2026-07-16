from browser import get_driver
from effect_details import scrape_effect
from effect_index import get_all_effects
from csv_utils import save_csv
from pathlib import Path
import time
import random

BASE_DIR = Path(__file__).resolve().parent.parent

driver = get_driver()

effects = get_all_effects(driver)

print("Effects:", len(effects))
print(effects)

print("Number of effects found:", len(effects))

if len(effects) > 0:
    print("First effect:", effects[0])
else:
    print("No effects found!")

master_dataset = []

for i, effect in enumerate(effects, start=1):

    

    hats = scrape_effect(
        driver,
        effect["effect_name"]
    )

    master_dataset.extend(hats)

    save_csv(
        master_dataset,
        "data/all_unusuals.csv"
    )

    print(
    f"[{i}/{len(effects)}] "
    f"{effect['effect_name']} "
    f"| {len(hats)} hats "
    f"| Total rows: {len(master_dataset)}"
)

    time.sleep(1)


    




print("Done!")

