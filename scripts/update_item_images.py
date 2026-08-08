"""Build a small TF2 item-image catalogue from Steam's official schema."""
from __future__ import annotations
import json, os
from pathlib import Path
import requests

URL = "https://api.steampowered.com/IEconItems_440/GetSchemaItems/v0001/"
OUT = Path("generated/item_images.json")

def main():
    key = os.environ.get("STEAM_WEB_API_KEY")
    if not key: raise RuntimeError("Missing STEAM_WEB_API_KEY")
    start = 0; by_defindex = {}; by_name = {}
    while True:
        r = requests.get(URL, params={"key": key, "language": "en", "start": start}, timeout=60); r.raise_for_status()
        result = r.json().get("result", {})
        for item in result.get("items", []):
            image = item.get("image_url_large") or item.get("image_url")
            name = item.get("item_name")
            index = item.get("defindex")
            if image and name and index is not None:
                entry = {"item_name": name, "image_url": image}
                by_defindex[str(index)] = entry; by_name.setdefault(name.casefold(), entry)
        next_start = result.get("next")
        if next_start is None: break
        start = int(next_start)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"by_defindex": by_defindex, "by_name": by_name}, indent=2), encoding="utf-8")
    print(f"Saved {len(by_defindex):,} item images to {OUT}")
if __name__ == "__main__": main()
