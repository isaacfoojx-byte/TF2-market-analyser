"""Shared, deterministic snapshot cleaning audit and comparison rules."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd

CLEANING_VERSION = "2.0"
PRICE_PATTERN = re.compile(
    r"^((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)\s*"
    r"(?:[-\u2013\u2014]\s*((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?))?\s*(keys?|ref)$",
    re.IGNORECASE,
)


def parse_price(value):
    """Accept an entire positive range, never extract numbers from malformed text."""
    match = PRICE_PATTERN.fullmatch(str(value).strip())
    if not match:
        return float("nan"), float("nan"), ""
    low, high = float(match[1].replace(",", "")), float((match[2] or match[1]).replace(",", ""))
    if not all(math.isfinite(x) and x > 0 for x in (low, high)) or high < low:
        return float("nan"), float("nan"), ""
    return low, high, "keys" if match[3].lower().startswith("key") else "ref"


def positive(value):
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (ValueError, TypeError):
        return False


def price_status(value):
    if pd.isna(value) or str(value).strip() == "":
        return "missing"
    try:
        number = float(value)
    except (ValueError, TypeError):
        return "invalid"
    if not math.isfinite(number) or number < 0:
        return "invalid"
    return "zero" if number == 0 else "priced"


def normalise_text(value):
    return "" if pd.isna(value) else " ".join(str(value).split())


def market_id(row, schema):
    if schema == "unusual":
        numbers = [pd.to_numeric(row.get(k), errors="coerce") for k in ("defindex", "effect_id")]
        if not all(positive(n) and float(n).is_integer() for n in numbers):
            return ""
        return f"tf2:unusual:{int(numbers[0])}:{int(numbers[1])}:tradable:craftable"
    name, quality = [normalise_text(row.get(k)).casefold() for k in ("item_name", "quality")]
    craftable = str(row.get("craftable", "")).strip().lower()
    if craftable in {"true", "1", "1.0"}:
        craftable = "craftable"
    elif craftable in {"false", "0", "0.0"}:
        craftable = "noncraftable"
    else:
        return ""
    if not name or not quality:
        return ""
    # Indexed API names include their priceindex suffix. Legacy captures have no
    # reliable numeric definition ID; do not silently invent one.
    key = json.dumps([name, quality, craftable, "tradable"], ensure_ascii=True)
    return "tf2:community:" + hashlib.sha256(key.encode()).hexdigest()[:32]


def source_time(value):
    if pd.isna(value) or str(value).strip() == "":
        return ""
    try:
        numeric = float(value)
    except (ValueError, TypeError):
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
    else:
        parsed = pd.to_datetime(numeric, unit="s", errors="coerce", utc=True) if positive(numeric) else pd.NaT
    return "" if pd.isna(parsed) else parsed.isoformat()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def previous_snapshot(output_path, schema, previous_dir=None):
    directory = Path(previous_dir) if previous_dir is not None else output_path.parent
    pattern = "cleaned_*.csv" if schema == "unusual" else "community_prices_*.csv"
    candidates = [p for p in directory.glob(pattern) if p.name < output_path.name]
    return max(candidates, key=lambda p: p.name) if candidates else None


def write_cleaned(raw_path, original, cleaned, reasons, output_path, schema,
                  previous_dir=None, change_threshold=0.5):
    """Write accepted data, a full row audit, and a content-linked JSON report.

    `cleaned` retains the original zero-based DataFrame index. Rejected records
    remain in the row audit with their original field values.
    """
    if Path(raw_path).resolve() == Path(output_path).resolve():
        raise ValueError("Cleaned output must not overwrite the raw snapshot")
    if not math.isfinite(change_threshold) or change_threshold <= 0:
        raise ValueError("Change threshold must be positive and finite")
    price_col = "bp_price_keys_equivalent" if schema == "unusual" else "price_keys_equivalent"
    cleaned = cleaned.copy()
    cleaned["market_id"] = cleaned.apply(lambda r: market_id(r, schema), axis=1) if len(cleaned) else pd.Series(dtype=str)
    cleaned["collected_at"] = original.loc[cleaned.index, "scrape_timestamp"]
    cleaned["cleaning_version"] = CLEANING_VERSION
    cleaned["price_status"] = "priced"
    cleaned["source_updated_at"] = cleaned.get(
        "source_last_update", pd.Series("", index=cleaned.index),
    ).map(source_time)
    flags = {i: [] for i in cleaned.index}
    for i, row in cleaned.iterrows():
        collection = pd.Timestamp(row["collected_at"])
        if collection.tzinfo is None:
            flags[i].append("collection_timezone_unknown")
        if not row["source_updated_at"]:
            flags[i].append("source_update_unknown")
        elif collection.tzinfo is not None and pd.Timestamp(row["source_updated_at"]) > collection:
            flags[i].append("source_update_after_collection")
        if schema == "community":
            flags[i].append("name_based_identity")
        if row.get("key_rate_source") == "supplied_approximation":
            flags[i].append("approximate_key_rate")
        if not positive(row.get("source_price_low")):
            flags[i].append("source_range_unavailable")
        if row.get("source_price_provenance") == "derived_key_display":
            flags[i].append("original_currency_unknown")

    previous = previous_snapshot(output_path, schema, previous_dir)
    comparison = {"status": "no_previous_snapshot", "threshold_fraction": change_threshold}
    if previous is not None:
        old = pd.read_csv(previous)
        old_ids = old.apply(lambda r: market_id(r, schema), axis=1)
        if old_ids.eq("").any() or old_ids.duplicated().any():
            comparison.update(status="ambiguous_previous_identity", previous_file=previous.name)
        else:
            old_prices = dict(zip(old_ids, pd.to_numeric(old[price_col], errors="coerce")))
            current_ids = set(cleaned["market_id"])
            observed_ids = {market_id(r, schema) for _, r in original.iterrows()} - {""}
            changes = {}
            for i, row in cleaned.iterrows():
                prior = old_prices.get(row["market_id"])
                if positive(prior):
                    change = float(row[price_col]) / float(prior) - 1
                    changes[i] = change
                    if abs(change) >= change_threshold:
                        flags[i].append("large_price_change")
            cleaned["price_change_fraction"] = pd.Series(changes, dtype=float)
            comparison.update(
                status="compared", previous_file=previous.name,
                previous_sha256=file_hash(previous),
                appeared_market_ids=sorted(observed_ids - set(old_ids)),
                absent_market_ids=sorted(set(old_ids) - observed_ids),
                observed_but_rejected_market_ids=sorted((set(old_ids) & observed_ids) - current_ids),
                comparable_markets=len(changes),
            )
    cleaned["quality_flags"] = pd.Series({i: "|".join(f) for i, f in flags.items()}, dtype=str)
    cleaned["raw_row_number"] = cleaned.index + 2
    audit = original.copy()
    audit["raw_row_number"] = audit.index + 2
    audit["market_id"] = audit.apply(lambda r: market_id(r, schema), axis=1) if len(audit) else pd.Series(dtype=str)
    audit["disposition"] = ["accepted" if i in cleaned.index else "rejected" for i in audit.index]
    audit["rejection_reason"] = [reasons.get(i, "") for i in audit.index]
    raw_price_col = "bp_price_ref" if schema == "unusual" else "price_ref"
    audit["raw_price_status"] = audit[raw_price_col].map(price_status)
    audit["quality_flags"] = ["|".join(flags.get(i, [])) for i in audit.index]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    quality_dir = output_path.parent / "quality"
    quality_dir.mkdir(exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    audit.to_csv(quality_dir / f"{output_path.stem}.rows.csv", index=False)
    report = {
        "cleaning_version": CLEANING_VERSION, "schema": schema,
        "raw_file": Path(raw_path).name, "raw_sha256": file_hash(raw_path),
        "processed_file": output_path.name, "processed_sha256": file_hash(output_path),
        "collection_timestamps": sorted(original["scrape_timestamp"].dropna().astype(str).unique().tolist()),
        "key_rates_ref": sorted(cleaned["key_price_ref"].dropna().unique().tolist()),
        "input_rows": len(original), "accepted_rows": len(cleaned),
        "rejected_rows": len(original) - len(cleaned),
        "rejection_counts": dict(Counter(reasons.values())),
        "warning_counts": dict(Counter(f for values in flags.values() for f in values)),
        "missing_fields": {c: int(original[c].isna().sum()) for c in original.columns if original[c].isna().any()},
        "raw_price_status_counts": dict(Counter(audit["raw_price_status"])),
        "comparison": comparison,
    }
    (quality_dir / f"{output_path.stem}.quality.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    return cleaned.reset_index(drop=True)

