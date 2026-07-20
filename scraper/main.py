from .browser import get_driver
from .effect_details import scrape_effect
from .effect_index import get_all_effects
from processing.clean_data import clean_data
from processing.key_price import get_key_market
from .csv_utils import save_csv
from pathlib import Path
import time


BASE_DIR = Path(__file__).resolve().parent.parent

driver = get_driver()

key_market = get_key_market(driver)

print("Current key market:")
print(key_market)

effects = get_all_effects(driver)

master_dataset = []

for i, effect in enumerate(effects, start=1):

    
    try:
        hats = scrape_effect(
            driver,
            effect["effect_name"]
        )

        master_dataset.extend(hats)

        save_csv(
            master_dataset,
            "data/raw/all_unusuals.csv"
        )

        print(
        f"[{i}/{len(effects)}] "
        f"{effect['effect_name']} "
        f"| {len(hats)} hats "
        f"| Total rows: {len(master_dataset)}"
    )

    except Exception as e:
        print(f"Failed: {effect['effect_name']} ({e})")
        
        

    time.sleep(0.2)  # Be nice to the server


    


driver.quit()

clean_data()

print("Done!")

