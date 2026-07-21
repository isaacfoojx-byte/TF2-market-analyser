from .browser import get_driver
from .effect_details import scrape_effect
from .effect_index import get_all_effects
from processing.clean_data import clean_data
from processing.key_price import get_key_market
from .csv_utils import save_csv
from pathlib import Path
import time
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

scrape_datetime = datetime.now()

scrape_timestamp = datetime.now().isoformat(timespec="seconds")

filename_timestamp = scrape_datetime.strftime("%Y-%m-%d_%H-%M-%S")

raw_csv = f"data/raw/unusuals_{filename_timestamp}.csv"
processed_csv = f"data/processed/cleaned_{filename_timestamp}.csv"

driver = get_driver()

current_key_price = get_key_market(driver)

print("Current key market:")
print(current_key_price)

effects = get_all_effects(driver)

master_dataset = []

for i, effect in enumerate(effects, start=1):

    
    try:
        hats = scrape_effect(
            driver,
            effect["effect_name"],
            scrape_timestamp
        )

        master_dataset.extend(hats)

        save_csv(
            master_dataset,
            raw_csv
        )

        print(
        f"[{i}/{len(effects)}] "
        f"{effect['effect_name']} "
        f"| {len(hats)} hats "
        f"| Total rows: {len(master_dataset)}"
    )

    except Exception as e:
        print(f"Failed: {effect['effect_name']} ({e})")
        
        

    time.sleep(0.05)  # Be nice to the server


    


driver.quit()

clean_data(raw_csv, processed_csv,current_key_price)

print("Done!")

