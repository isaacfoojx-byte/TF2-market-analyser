import json
from pathlib import Path


METADATA_FILE = Path("generated/metadata.json")


def save_metadata(
    snapshot_timestamp,
    key_price,
    total_listings,
    scrape_duration,
):
    metadata = {
        "snapshot_timestamp": snapshot_timestamp,
        "key_price": key_price,
        "total_listings": total_listings,
        "scrape_duration": scrape_duration,
    }

    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with METADATA_FILE.open("w") as f:
        json.dump(metadata, f, indent=4)


def load_metadata():
    if not METADATA_FILE.exists():
        return None

    with METADATA_FILE.open() as f:
        return json.load(f)