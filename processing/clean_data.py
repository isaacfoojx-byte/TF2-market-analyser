"""Clean Unusual captures while preserving raw inputs and a per-row audit."""
from pathlib import Path

import numpy as np
import pandas as pd

from processing.quality import market_id, parse_price, positive, write_cleaned


def parse_key_range(value):
    low, high, unit = parse_price(value)
    if unit != "keys":
        return pd.Series([np.nan, np.nan, np.nan])
    return pd.Series([low, high, (low + high) / 2])


def clean_data(raw_csv, processed_csv, current_key_price, *,
               previous_processed_dir=None, key_rate_source="supplied",
               change_threshold=0.5):
    if not positive(current_key_price):
        raise ValueError("Key conversion rate must be positive and finite")
    raw_path, output_path = Path(raw_csv), Path(processed_csv)
    original = pd.read_csv(raw_path)
    required = {"defindex", "effect_id", "item_name", "scrape_timestamp",
                "bp_price_ref", "bp_price_keys"}
    missing = required - set(original.columns)
    if missing:
        raise ValueError(f"Unusual snapshot missing columns: {', '.join(sorted(missing))}")
    frame = original.copy()
    frame["item_name"] = frame["item_name"].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    frame["bp_price_ref"] = pd.to_numeric(frame["bp_price_ref"], errors="coerce")
    timestamps = pd.to_datetime(frame["scrape_timestamp"], errors="coerce", format="mixed", utc=True)
    if timestamps.dropna().nunique() > 1:
        raise ValueError("Snapshot contains multiple collection timestamps")
    reasons = {}
    for i, row in frame.iterrows():
        if not market_id(row, "unusual") or pd.isna(row["item_name"]) or not row["item_name"]:
            reasons[i] = "invalid_market_identity"
        elif pd.isna(timestamps[i]):
            reasons[i] = "invalid_collection_timestamp"
        elif not positive(row["bp_price_ref"]):
            reasons[i] = "missing_or_invalid_price"
    frame = frame.drop(index=list(reasons)).copy()
    for col in ("effect_id", "defindex"):
        frame[col] = pd.to_numeric(frame[col]).astype("int64")
    duplicate = frame.duplicated(["effect_id", "defindex"], keep=False)
    # Conflicting observations cannot be chosen safely from row order.
    for _, group in frame.loc[duplicate].groupby(["effect_id", "defindex"]):
        compare_cols = [c for c in ("bp_price_ref", "bp_price_keys", "source_value", "source_value_high", "source_currency") if c in group]
        if len(group[compare_cols].drop_duplicates()) > 1:
            for i in group.index:
                reasons[i] = "conflicting_duplicate"
        else:
            for i in group.index[:-1]:
                reasons[i] = "duplicate_observation"
    frame = frame.drop(index=[i for i in reasons if i in frame.index]).copy()
    frame["usd_price"] = pd.to_numeric(
        frame.get("bp_price_all", pd.Series("", index=frame.index)).astype("string")
        .str.extract(r"\$([\d,]+(?:\.\d+)?)")[0].str.replace(",", "", regex=False),
        errors="coerce",
    )
    ranges = [parse_key_range(v).tolist() for v in frame["bp_price_keys"]]
    frame[["key_low", "key_high", "key_mid"]] = pd.DataFrame(ranges, index=frame.index, columns=["key_low", "key_high", "key_mid"])
    frame["item_type"] = frame.get("slot", pd.Series("", index=frame.index)).map({
        "misc": "cosmetic", "taunt": "taunt", "primary": "weapon",
        "secondary": "weapon", "melee": "weapon",
    }).fillna("unknown")
    frame.loc[frame["item_name"].eq("War Paint"), "item_type"] = "war_paint"
    frame["key_price_ref"] = float(current_key_price)
    frame["key_rate_source"] = key_rate_source
    frame["bp_price_keys_equivalent"] = frame["bp_price_ref"] / float(current_key_price)
    frame["has_price"] = True
    if "source_value" in frame:
        frame["source_price_low"] = pd.to_numeric(frame["source_value"], errors="coerce")
        frame["source_price_high"] = pd.to_numeric(frame["source_value_high"], errors="coerce") if "source_value_high" in frame else frame["source_price_low"]
        frame["source_price_unit"] = frame["source_currency"].replace({"metal": "ref"})
        frame["source_price_provenance"] = "api_original"
    else:
        frame["source_price_low"] = frame["key_low"]
        frame["source_price_high"] = frame["key_high"]
        frame["source_price_unit"] = "keys"
        frame["source_price_provenance"] = "derived_key_display"
    invalid = ~frame["bp_price_keys_equivalent"].map(positive)
    if "source_value" in frame:
        invalid |= (~frame["source_price_low"].map(positive)
                    | ~frame["source_price_high"].map(positive)
                    | frame["source_price_high"].lt(frame["source_price_low"])
                    | ~frame["source_price_unit"].isin(["keys", "ref"]))
    reasons.update({i: "invalid_normalized_or_source_price" for i in frame.index[invalid]})
    frame = frame.loc[~invalid].copy()
    result = write_cleaned(raw_path, original, frame, reasons, output_path, "unusual",
                           previous_processed_dir, change_threshold)
    print(f"Saved {len(result):,} cleaned rows; rejected {len(reasons):,}; quality report in {output_path.parent / 'quality'}")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_csv", type=Path)
    parser.add_argument("processed_csv", type=Path)
    parser.add_argument("--key-price-ref", type=float, required=True)
    parser.add_argument("--previous-processed-dir", type=Path)
    parser.add_argument("--change-threshold", type=float, default=0.5)
    parser.add_argument("--key-rate-source", default="supplied_approximation")
    args = parser.parse_args()
    clean_data(args.raw_csv, args.processed_csv, args.key_price_ref,
               previous_processed_dir=args.previous_processed_dir,
               key_rate_source=args.key_rate_source, change_threshold=args.change_threshold)
