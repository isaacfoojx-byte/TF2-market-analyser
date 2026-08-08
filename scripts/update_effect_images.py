"""Build a catalogue of official TF2 Wiki previews for tracked unusual effects."""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
import json
from pathlib import Path

import requests


API_URL = "https://wiki.teamfortress.com/w/api.php"
PROCESSED_DIR = Path("data/processed")
OUT = Path("generated/effect_images.json")
USER_AGENT = "TFAnalytics/1.0 (effect preview catalogue)"


def tracked_effect_names() -> list[str]:
    """Return every effect name found in processed unusual-market snapshots."""

    names: set[str] = set()
    for snapshot in PROCESSED_DIR.glob("*.csv"):
        with snapshot.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                name = (row.get("effect_name") or "").strip()
                if name:
                    names.add(name)

    return sorted(names, key=str.casefold)


def fetch_preview_url(effect_name: str) -> str | None:
    """Find the best matching official Wiki image for one unusual effect."""

    response = requests.get(
        API_URL,
        params={
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "search",
            "gsrsearch": f"Unusual {effect_name}",
            "gsrnamespace": 6,
            "gsrlimit": 10,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 128,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()

    pages = response.json().get("query", {}).get("pages", [])
    expected_title = f"unusual {effect_name}".casefold()

    def score(page: dict) -> tuple[int, str]:
        title = str(page.get("title", "")).removeprefix("File:").casefold()
        if title.startswith(expected_title):
            return (2, title)
        if expected_title in title:
            return (1, title)
        return (0, title)

    for page in sorted(pages, key=score, reverse=True):
        if score(page)[0] == 0:
            continue
        image_info = page.get("imageinfo") or []
        if image_info:
            return image_info[0].get("thumburl") or image_info[0].get("url")

    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process this many effects (useful for a quick smoke test).",
    )
    args = parser.parse_args()

    effect_names = tracked_effect_names()
    if args.limit is not None:
        effect_names = effect_names[: max(args.limit, 0)]
    if not effect_names:
        raise RuntimeError("No processed unusual-market snapshots were found.")

    images: dict[str, str] = {}
    unmatched: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fetch_preview_url, name): name
            for name in effect_names
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                image_url = future.result()
            except requests.RequestException as error:
                print(f"Could not look up {name}: {error}")
                unmatched.append(name)
                continue

            if image_url:
                images[name.casefold()] = image_url
            else:
                unmatched.append(name)

    if not images:
        raise RuntimeError("The TF2 Wiki did not return any effect previews.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "images": images,
                "unmatched": sorted(unmatched, key=str.casefold),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved {len(images):,} effect previews to {OUT}.")
    print(f"No Wiki preview found for {len(unmatched):,} effects.")


if __name__ == "__main__":
    main()
