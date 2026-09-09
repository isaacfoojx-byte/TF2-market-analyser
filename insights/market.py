"""Descriptions of guide-price evidence, never inferred trading volume."""
import numpy as np
import pandas as pd


def calculate_market_sentiment(comparison):
    """A direction score centered at 50; unchanged markets stay in the denominator."""
    if not {"status", "price_change"}.issubset(comparison.columns):
        return {"score": None, "label": "Insufficient data", "confidence": "Low",
                "reason": "Comparable guide-price data is unavailable."}
    matched = comparison.loc[comparison.status.isin(["Price Increased", "Price Decreased", "Unchanged"])].copy()
    matched = matched.loc[np.isfinite(pd.to_numeric(matched.price_change, errors="coerce"))]
    total = len(matched)
    if not total:
        return {"score": None, "label": "Insufficient data", "confidence": "Low",
                "reason": "No comparable priced markets were found."}
    rising = int(matched.status.eq("Price Increased").sum())
    falling = int(matched.status.eq("Price Decreased").sum())
    unchanged = total - rising - falling
    score = round(50 + 50 * (rising - falling) / total)
    overlap = total / len(comparison)
    age = matched.get("source_age_days_new", pd.Series(np.nan, index=matched.index))
    recent = age.between(0, 30).sum() / total
    confidence = "High" if total >= 100 and overlap >= .8 and recent >= .8 else "Medium" if total >= 25 and overlap >= .5 else "Low"
    reason = (f"{total:,} markets have prices at both endpoints ({overlap:.1%} of the union). "
              f"{recent:.1%} have a known source valuation age of at most 30 days. "
              "Evidence coverage does not establish liquidity or trading confidence.")
    return {
        "score": score, "label": "Rising" if score >= 60 else "Falling" if score <= 40 else "Mixed / steady",
        "confidence": confidence, "confidence_reason": reason,
        "rising_markets": rising, "falling_markets": falling, "unchanged_markets": unchanged,
        "comparable_markets": total, "breadth_percent": rising / total * 100,
        "falling_percent": falling / total * 100, "unchanged_percent": unchanged / total * 100,
        "median_change_keys": float(matched.price_change.median()),
        "reason": f"{rising:,} ({rising / total:.2%}) rose, {falling:,} ({falling / total:.2%}) fell, and {unchanged:,} ({unchanged / total:.2%}) were unchanged among {total:,} comparable markets.",
    }


def detect_market_risks(comparison):
    sentiment = calculate_market_sentiment(comparison)
    if sentiment["score"] is None:
        return [sentiment["reason"]]
    warnings = []
    if sentiment["confidence"] == "Low":
        warnings.append("Limited comparable coverage: interpret the price direction cautiously.")
    if "_merge" in comparison and comparison._merge.ne("both").any():
        warnings.append("Coverage changed between snapshots; entering or leaving coverage is not evidence of supply or sales.")
    age = comparison.get("source_age_days_new", pd.Series(np.nan, index=comparison.index))
    if age.isna().any():
        warnings.append("Some source valuation ages are unknown; repeated collection does not establish a fresh valuation.")
    if age.gt(30).any():
        warnings.append(f"{int(age.gt(30).sum()):,} source valuations are over 30 days old at collection (review threshold).")
    changes = pd.to_numeric(comparison.get("percent_change", pd.Series(dtype=float)), errors="coerce").dropna()
    if changes.abs().ge(25).any():
        warnings.append("Some guide prices moved at least 25%; inspect source revisions and currency conversion before interpreting the change.")
    return warnings or ["No broad data-quality warning was triggered in this comparison."]


def build_market_story(comparison, summary):
    sentiment = calculate_market_sentiment(comparison)
    risks = detect_market_risks(comparison)
    if sentiment["score"] is None:
        return {"headline": "Market update unavailable", "summary": sentiment["reason"],
                "confidence": "Low", "confidence_reason": sentiment["reason"],
                "risk": "High", "risk_reasons": risks}
    return {
        "headline": f"Guide-price direction: {sentiment['label'].lower()}",
        "summary": sentiment["reason"], "confidence": sentiment["confidence"],
        "confidence_reason": sentiment["confidence_reason"],
        "risk": "Low" if risks[0].startswith("No broad") else "Medium", "risk_reasons": risks,
        "rising_markets": sentiment["breadth_percent"], "falling_markets": sentiment["falling_percent"],
        "unchanged_markets": sentiment["unchanged_percent"], "median_change_keys": sentiment["median_change_keys"],
    }


def find_price_movers(comparison, limit=10):
    """Rank rising guide prices only; no liquidity or opportunity score is inferred."""
    required = {"status", "percent_change", "effect_name", "item_name"}
    if not required.issubset(comparison.columns):
        return pd.DataFrame()
    return comparison.loc[comparison.status.eq("Price Increased")].sort_values(
        "percent_change", ascending=False,
    ).head(limit).copy()


def generate_market_insights(comparison, summary):
    sentiment = calculate_market_sentiment(comparison)
    return [sentiment["reason"], *detect_market_risks(comparison)]
