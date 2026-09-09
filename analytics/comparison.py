"""Comparable guide prices, explicit coverage, and source-currency attribution."""

import numpy as np
import pandas as pd

from processing.quality import market_id


def prepare_markets(frame, schema):
    frame = frame.copy()
    for label in (["defindex", "effect_id", "item_name", "effect_name"] if schema == "unusual" else ["item_name", "quality", "craftable"]):
        if label not in frame:
            frame[label] = pd.Series(index=frame.index, dtype=object)
    price = "bp_price_keys_equivalent" if schema == "unusual" else "price_keys_equivalent"
    ref = "bp_price_ref" if schema == "unusual" else "price_ref"
    for name in [price, ref, "key_price_ref", "source_price_low", "source_price_high"]:
        frame[name] = pd.to_numeric(frame.get(name, pd.Series(index=frame.index, dtype=float)), errors="coerce")
    if schema == "unusual":
        item = pd.to_numeric(frame.get("defindex", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        effect = pd.to_numeric(frame.get("effect_id", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        valid_id = item.gt(0) & effect.gt(0) & np.isfinite(item) & np.isfinite(effect) & item.mod(1).eq(0) & effect.mod(1).eq(0)
        frame["market_id"] = ""
        frame.loc[valid_id, "market_id"] = "tf2:unusual:" + item.loc[valid_id].astype("int64").astype(str) + ":" + effect.loc[valid_id].astype("int64").astype(str) + ":tradable:craftable"
    else:
        frame["market_id"] = frame.apply(lambda row: market_id(row, schema), axis=1) if len(frame) else pd.Series(dtype=str)
    frame = frame.loc[frame.market_id.ne("")].copy()
    frame["average_price"] = frame[price].where(np.isfinite(frame[price]) & frame[price].gt(0))
    if "has_price" in frame:
        has_price = frame.has_price.astype(str).str.lower().isin(["true", "1", "1.0"])
        frame.loc[~has_price, "average_price"] = np.nan
    # Duplicate CSV entries are observations, never counts of listings or sales.
    groups = frame.groupby("market_id", sort=False)
    counts = groups.size()
    conflicts = groups["average_price"].nunique(dropna=False).gt(1)
    rates_conflict = groups["key_price_ref"].nunique(dropna=False).gt(1)
    attribution_conflict = rates_conflict.copy()
    for column in ["source_price_low", "source_price_high", "source_price_unit"]:
        if column in frame:
            attribution_conflict |= groups[column].nunique(dropna=False).gt(1)
    frame = frame.drop_duplicates("market_id", keep="last").set_index("market_id")
    frame["observation_count"] = counts
    frame["ambiguous_price"] = conflicts
    frame.loc[conflicts, "average_price"] = np.nan
    frame.loc[rates_conflict, "key_price_ref"] = np.nan
    frame["median_price"] = frame["average_price"]
    frame["guide_price_ref"] = frame[ref]
    frame["guide_price_keys"] = frame["average_price"]
    for column in ["source_price_unit", "source_price_provenance", "source_updated_at", "collected_at", "scrape_timestamp"]:
        if column not in frame:
            frame[column] = None
    frame.loc[attribution_conflict, "source_price_unit"] = None
    collected = pd.to_datetime(frame["collected_at"].fillna(frame["scrape_timestamp"]), errors="coerce", utc=True, format="mixed")
    updated = pd.to_datetime(frame["source_updated_at"], errors="coerce", utc=True, format="mixed")
    age = (collected - updated).dt.total_seconds() / 86400
    frame["source_age_days"] = age.where(age.ge(0))
    if "quality_flags" in frame:
        frame.loc[frame.quality_flags.fillna("").str.contains("collection_timezone_unknown", regex=False), "source_age_days"] = np.nan
    return frame.reset_index()


def compare_frames(old, new, schema="unusual"):
    left, right = prepare_markets(old, schema), prepare_markets(new, schema)
    result = left.merge(right, on="market_id", how="outer", suffixes=("_old", "_new"), indicator=True, validate="one_to_one")
    for column in ["effect_id", "defindex", "effect_name", "item_name", "quality", "craftable"]:
        if column + "_new" in result and column + "_old" in result:
            result[column] = result[column + "_new"].where(result[column + "_new"].notna(), result[column + "_old"])
    result["comparable"] = result._merge.eq("both") & result.average_price_old.notna() & result.average_price_new.notna()
    result["price_change"] = (result.average_price_new - result.average_price_old).where(result.comparable)
    result["price_change_keys"] = result.price_change
    result["percent_change"] = result.price_change / result.average_price_old * 100
    result["status"] = "Unpriced or ambiguous"
    result.loc[result._merge.eq("right_only"), "status"] = "Entered coverage"
    result.loc[result._merge.eq("left_only"), "status"] = "Left coverage"
    result.loc[result.comparable, "status"] = "Unchanged"
    result.loc[result.price_change.gt(1e-9), "status"] = "Price Increased"
    result.loc[result.price_change.lt(-1e-9), "status"] = "Price Decreased"
    result["item_component_keys"] = np.nan
    result["key_rate_component_keys"] = np.nan
    result["decomposition_status"] = "Unavailable: original currency or rate missing"
    unit = result.source_price_unit_new
    known = result.comparable & unit.eq(result.source_price_unit_old) & unit.isin(["keys", "ref"])
    for side in ["old", "new"]:
        known &= ~result[f"source_price_provenance_{side}"].eq("derived_key_display")
        if f"key_rate_source_{side}" in result:
            known &= ~result[f"key_rate_source_{side}"].eq("supplied_approximation")
        low, high = result[f"source_price_low_{side}"], result[f"source_price_high_{side}"]
        known &= low.gt(0) & high.ge(low) & np.isfinite(low) & np.isfinite(high)
    low_old, high_old = result.source_price_low_old, result.source_price_high_old
    low_new, high_new = result.source_price_low_new, result.source_price_high_new
    mid_old, mid_new = low_old / 2 + high_old / 2, low_new / 2 + high_new / 2
    # For prices originally quoted in keys, a metal/key change contributes zero.
    keys = known & unit.eq("keys") & np.isclose(mid_old, result.average_price_old, rtol=1e-5) & np.isclose(mid_new, result.average_price_new, rtol=1e-5)
    result.loc[keys, "item_component_keys"] = result.loc[keys, "price_change"]
    result.loc[keys, "key_rate_component_keys"] = 0.0
    old_rate, new_rate = result.key_price_ref_old, result.key_price_ref_new
    ref = known & unit.eq("ref") & old_rate.gt(0) & new_rate.gt(0) & np.isfinite(old_rate) & np.isfinite(new_rate)
    ref &= np.isclose(mid_old / old_rate, result.average_price_old, rtol=1e-5) & np.isclose(mid_new / new_rate, result.average_price_new, rtol=1e-5)
    item = (mid_new - mid_old) / old_rate
    result.loc[ref, "item_component_keys"] = item.loc[ref]
    result.loc[ref, "key_rate_component_keys"] = result.loc[ref, "price_change"] - item.loc[ref]
    result.loc[keys | ref, "decomposition_status"] = "Available"
    return result


def compare_files(old_snapshot, new_snapshot, schema="unusual"):
    result = compare_frames(pd.read_csv(old_snapshot), pd.read_csv(new_snapshot), schema)
    result.attrs.update(old_snapshot=str(old_snapshot), new_snapshot=str(new_snapshot))
    return result


def comparison_summary(comparison):
    matched = comparison.loc[comparison.comparable]
    return {
        "comparable_markets": len(matched),
        "entered_coverage": int(comparison._merge.eq("right_only").sum()),
        "left_coverage": int(comparison._merge.eq("left_only").sum()),
        "unpriced_or_ambiguous": int((comparison._merge.eq("both") & ~comparison.comparable).sum()),
        "matched_mean_percent_change": matched.percent_change.mean() if len(matched) else np.nan,
        "matched_median_percent_change": matched.percent_change.median() if len(matched) else np.nan,
        "overlap_percent": len(matched) / len(comparison) * 100 if len(comparison) else np.nan,
        "known_source_ages": int(matched.source_age_days_new.notna().sum()),
        "median_source_age_days": matched.source_age_days_new.dropna().median() if matched.source_age_days_new.notna().any() else np.nan,
        "decomposed_markets": int(matched.decomposition_status.eq("Available").sum()),
    }


def trend_statistics(trend, price_column):
    prices = pd.to_numeric(trend[price_column], errors="coerce")
    changes = prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan) * 100
    usable = changes.dropna()
    observed = prices.notna()
    updated = pd.to_datetime(trend.get("source_updated_at", pd.Series(dtype=str)), errors="coerce", utc=True, format="mixed").dropna()
    timestamps = pd.to_datetime(trend["snapshot_timestamp"], utc=True, errors="coerce")
    gaps = timestamps.diff().dt.total_seconds() / 86400
    return {
        "largest_capture_gap_days": float(gaps.max()) if gaps.notna().any() else None,
        "observed_snapshots": int(observed.sum()), "missing_snapshots": int((~observed).sum()),
        "comparable_intervals": len(usable), "rising_intervals": int(usable.gt(1e-9).sum()),
        "falling_intervals": int(usable.lt(-1e-9).sum()), "unchanged_intervals": int(usable.abs().le(1e-9).sum()),
        "distinct_source_updates": int(updated.nunique()),
    }
