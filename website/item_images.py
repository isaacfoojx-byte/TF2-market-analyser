from __future__ import annotations
from html import escape
import json
from pathlib import Path

ITEM_CATALOG = Path("generated/item_images.json")
EFFECT_CATALOG = Path("generated/effect_images.json")


def load_catalog():
    if not ITEM_CATALOG.is_file(): return {"by_defindex": {}, "by_name": {}}
    try: return json.loads(ITEM_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {"by_defindex": {}, "by_name": {}}


def item_image(defindex=None, item_name=None):
    data = load_catalog()
    entry = data.get("by_defindex", {}).get(str(defindex)) if defindex is not None else None
    entry = entry or data.get("by_name", {}).get(str(item_name).casefold())
    return entry.get("image_url") if entry else None


def load_effect_catalog():
    if not EFFECT_CATALOG.is_file():
        return {"images": {}}
    try:
        return json.loads(EFFECT_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"images": {}}


def effect_preview_url(effect_name):
    """Return a saved official preview URL, if the catalogue has one."""

    return load_effect_catalog().get("images", {}).get(str(effect_name).casefold())


def effect_icon_html(effect_id, effect_name, width=72):
    """Return a browser-loaded official preview for an unusual effect."""

    image_url = effect_preview_url(effect_name)
    if not image_url:
        return None

    size = max(1, int(width))
    return (
        f'<img src="{image_url}" '
        f'alt="{escape(str(effect_name))}" '
        f'width="{size}" height="{size}" '
        'style="display:block; object-fit:contain;" loading="lazy">'
    )
