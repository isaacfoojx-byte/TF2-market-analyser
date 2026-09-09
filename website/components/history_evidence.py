"""Present historical comparison evidence and its limitations."""
import pandas as pd
import streamlit as st
from analytics.comparison import comparison_summary, trend_statistics


def change_label(value):
    return "Unavailable" if pd.isna(value) else f"{value:+.2f}%"


def comparison_evidence(comparison):
    summary = comparison_summary(comparison)
    columns = st.columns(4)
    for column, (label, value) in zip(columns, [
        ("Comparable markets", summary["comparable_markets"]),
        ("Entered coverage", summary["entered_coverage"]),
        ("Left coverage", summary["left_coverage"]),
        ("Median matched change", change_label(summary["matched_median_percent_change"])),
    ]):
        column.metric(label, value)
    st.caption(
        f"{summary['unpriced_or_ambiguous']:,} markets are present at both endpoints but lack an unambiguous usable price. "
        "Coverage refers to these processed datasets; leaving coverage is not a sale or a price of zero. "
        "Missing or rejected source rows can also change processed coverage."
    )
    st.caption(
        f"Source valuation age is known for {summary['known_source_ages']:,} comparable markets; "
        f"currency attribution is available for {summary['decomposed_markets']:,}. "
        "Age is measured at collection, not at the time you open this page."
    )
    with st.expander("Inspect price changes and currency conversion"):
        st.caption(
            "For ref-quoted prices, item movement is converted at the old key rate; the remaining change is the rate effect. "
            "For key-quoted prices, the rate contribution is zero. Components sum to the key-price change. "
            "This is arithmetic attribution, not a claim about why the market moved. Missing source details remain unavailable."
        )
        names = [c for c in ["item_name", "effect_name", "quality", "craftable"] if c in comparison]
        columns = names + ["status", "average_price_old", "average_price_new", "percent_change",
                           "item_component_keys", "key_rate_component_keys", "decomposition_status", "source_age_days_new"]
        st.dataframe(comparison[columns], hide_index=True)


def trend_evidence(trend, price_column):
    evidence = trend_statistics(trend, price_column)
    gap = evidence["largest_capture_gap_days"]
    if gap is not None and gap > 1.5:
        st.caption(f"Largest gap between saved captures: {gap:.1f} days. Intervals are not necessarily daily.")
    st.caption(
        f"Observed in {evidence['observed_snapshots']} snapshots; missing/unpriced in {evidence['missing_snapshots']}. "
        f"Across {evidence['comparable_intervals']} adjacent comparable intervals: "
        f"{evidence['rising_intervals']} rose, {evidence['falling_intervals']} fell, "
        f"{evidence['unchanged_intervals']} were unchanged. "
        f"Distinct known source-update timestamps: {evidence['distinct_source_updates']}. "
        "Repeated captures are not independent price revisions; gaps are not filled."
    )


def trend_confidence(trend, price_column):
    evidence = trend_statistics(trend, price_column)
    ages = trend.get("source_age_days", pd.Series(index=trend.index, dtype=float))
    if (evidence["observed_snapshots"] >= 5 and evidence["missing_snapshots"] == 0
            and evidence["distinct_source_updates"] >= 5 and ages.between(0, 30).mean() >= .8):
        return "High"
    return "Medium" if evidence["observed_snapshots"] >= 3 else "Low"
