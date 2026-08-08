from __future__ import annotations
from html import escape
import json
from pathlib import Path
from urllib.parse import quote

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


def effect_preview_url(effect_name):
    """Return the official TF2 Wiki preview for an unusual effect.

    backpack.tf's particle-thumbnail URLs are not reliably available to
    embedded web apps. The TF2 Wiki files are public screenshots of each
    effect, shown here at a compact width.
    """

    filename = quote(f"Unusual {effect_name} RED.png")
    return (
        "https://wiki.teamfortress.com/wiki/Special:FilePath/"
        f"{filename}?width=128"
    )


def effect_icon_html(effect_id, effect_name, width=72):
    """Return a browser-loaded official preview for an unusual effect."""

    size = max(1, int(width))
    return (
        f'<img src="{effect_preview_url(str(effect_name))}" '
        f'alt="{escape(str(effect_name))}" '
        f'width="{size}" height="{size}" '
        'style="display:block; object-fit:contain;" loading="lazy">'
    )
