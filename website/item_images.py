from __future__ import annotations
import json
from pathlib import Path

CATALOG = Path("generated/item_images.json")
def load_catalog():
    if not CATALOG.is_file(): return {"by_defindex": {}, "by_name": {}}
    try: return json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {"by_defindex": {}, "by_name": {}}
def item_image(defindex=None, item_name=None):
    data = load_catalog()
    entry = data.get("by_defindex", {}).get(str(defindex)) if defindex is not None else None
    entry = entry or data.get("by_name", {}).get(str(item_name).casefold())
    return entry.get("image_url") if entry else None
def effect_icon(effect_id): return f"https://backpack.tf/images/440/particles/{int(effect_id)}_94x94.png"
