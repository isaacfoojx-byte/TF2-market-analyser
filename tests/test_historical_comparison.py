import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from analytics.comparison import compare_frames, comparison_summary, trend_statistics
from analytics.history import load_unusual_trend
from insights.market import calculate_market_sentiment, find_price_movers


def market(item=1, price=2, **extra):
    row = dict(defindex=item, effect_id=6, item_name=f"Hat {item}", effect_name="Confetti",
               bp_price_keys_equivalent=price, bp_price_ref=price * 50,
               has_price=True, scrape_timestamp="2026-09-09T00:00:00+00:00")
    row.update(extra)
    return row


def compare(old, new):
    return compare_frames(pd.DataFrame(old), pd.DataFrame(new))


class HistoricalComparisonTests(unittest.TestCase):
    def test_names_can_change_without_creating_a_new_unusual_market(self):
        result = compare([market()], [market(price=3, item_name="Renamed Hat", effect_name="Renamed Effect")])
        self.assertEqual(len(result), 1)
        self.assertTrue(result.iloc[0].comparable)
        self.assertEqual(result.iloc[0].item_name, "Renamed Hat")
        self.assertEqual(result.iloc[0].percent_change, 50)

    def test_coverage_and_unpriced_are_not_zero_or_unchanged(self):
        result = compare([market(1), market(2), market(3)], [market(1), market(3, price=np.nan), market(4, price=1000)])
        summary = comparison_summary(result)
        self.assertEqual(summary["comparable_markets"], 1)
        self.assertEqual(summary["entered_coverage"], 1)
        self.assertEqual(summary["left_coverage"], 1)
        self.assertEqual(summary["unpriced_or_ambiguous"], 1)
        self.assertEqual(summary["matched_median_percent_change"], 0)
        self.assertTrue(result.loc[~result.comparable, "price_change"].isna().all())

    def test_unchanged_markets_are_in_direction_denominator(self):
        result = compare([market(i) for i in range(1, 101)], [market(i, price=3 if i == 1 else 2) for i in range(1, 101)])
        sentiment = calculate_market_sentiment(result)
        self.assertEqual(sentiment["comparable_markets"], 100)
        self.assertEqual(sentiment["breadth_percent"], 1)
        self.assertEqual(sentiment["unchanged_markets"], 99)
        self.assertEqual(sentiment["median_change_keys"], 0)

    def test_all_unchanged_is_neutral_not_insufficient_or_falling(self):
        sentiment = calculate_market_sentiment(compare([market()], [market()]))
        self.assertEqual(sentiment["score"], 50)
        self.assertEqual(sentiment["falling_percent"], 0)

    def test_ref_item_unchanged_rate_move_is_attributed_to_rate(self):
        old = market(price=2, key_price_ref=50, source_price_low=100, source_price_high=100, source_price_unit="ref")
        new = market(price=1, key_price_ref=100, source_price_low=100, source_price_high=100, source_price_unit="ref")
        row = compare([old], [new]).iloc[0]
        self.assertEqual(row.item_component_keys, 0)
        self.assertEqual(row.key_rate_component_keys, -1)
        self.assertEqual(row.decomposition_status, "Available")

    def test_components_sum_to_total_when_price_and_rate_both_change(self):
        old = market(price=2, key_price_ref=50, source_price_low=100, source_price_high=100, source_price_unit="ref")
        new = market(price=1.5, key_price_ref=100, source_price_low=150, source_price_high=150, source_price_unit="ref")
        row = compare([old], [new]).iloc[0]
        self.assertEqual(row.item_component_keys, 1)
        self.assertEqual(row.key_rate_component_keys, -1.5)
        self.assertEqual(row.price_change, row.item_component_keys + row.key_rate_component_keys)

    def test_keys_native_prices_have_no_rate_contribution(self):
        old = market(price=2, key_price_ref=50, source_price_low=2, source_price_high=2, source_price_unit="keys")
        new = market(price=2, key_price_ref=100, source_price_low=2, source_price_high=2, source_price_unit="keys")
        row = compare([old], [new]).iloc[0]
        self.assertEqual(row.item_component_keys, 0)
        self.assertEqual(row.key_rate_component_keys, 0)

    def test_legacy_missing_currency_is_not_inferred_from_normalized_price(self):
        row = compare([market()], [market(price=3)]).iloc[0]
        self.assertTrue(pd.isna(row.item_component_keys))
        self.assertTrue(pd.isna(row.source_age_days_new))

    def test_conflicting_duplicate_prices_are_not_averaged(self):
        row = compare([market(), market(price=4)], [market(price=3)]).iloc[0]
        self.assertFalse(row.comparable)
        self.assertTrue(pd.isna(row.percent_change))

    def test_source_age_is_measured_at_collection(self):
        row = compare([market()], [market(source_updated_at="2026-09-01T00:00:00Z")]).iloc[0]
        self.assertEqual(row.source_age_days_new, 8)

    def test_movers_do_not_require_invented_listing_counts(self):
        result = compare([market()], [market(price=3)])
        self.assertEqual(len(find_price_movers(result)), 1)
        self.assertNotIn("opportunity_score", result)
        self.assertNotIn("listings_new", result)

    def test_empty_endpoint_is_coverage_loss_not_a_zero_price(self):
        result = compare_frames(pd.DataFrame([market()]), pd.DataFrame())
        self.assertEqual(result.iloc[0].status, "Left coverage")
        self.assertTrue(pd.isna(result.iloc[0].price_change))

    def test_empty_source_timestamps_are_not_independent_updates(self):
        trend = pd.DataFrame({"snapshot_timestamp": ["2026-09-01", "2026-09-04"],
                              "price": [2, 2], "source_updated_at": ["", "invalid"]})
        evidence = trend_statistics(trend, "price")
        self.assertEqual(evidence["distinct_source_updates"], 0)
        self.assertEqual(evidence["largest_capture_gap_days"], 3)

    def test_missing_intermediate_snapshot_does_not_generate_a_return(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for day, rows in [(1, [market()]), (2, [market(2)]), (3, [market(price=4)])]:
                path = Path(directory) / f"cleaned_2026-09-0{day}_00-00-00.csv"
                for row in rows:
                    row["scrape_timestamp"] = f"2026-09-0{day}T00:00:00"
                pd.DataFrame(rows).to_csv(path, index=False)
                paths.append(path)
            with patch("analytics.history.get_snapshots", return_value=paths):
                trend = load_unusual_trend(6, 1)
            self.assertEqual(len(trend), 3)
            self.assertTrue(pd.isna(trend.iloc[1].median_price))
            self.assertTrue(trend.percent_change.isna().all())
            evidence = trend_statistics(trend, "median_price")
            self.assertEqual(evidence["missing_snapshots"], 1)
            self.assertEqual(evidence["comparable_intervals"], 0)


if __name__ == "__main__":
    unittest.main()
