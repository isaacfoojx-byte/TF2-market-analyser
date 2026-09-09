import json
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from processing.clean_data import clean_data
from processing.community_prices import clean_community_prices, backfill_key_price
from processing.quality import market_id, parse_price
from scripts.snapshot_quality_report import verify_quality_report
from scripts.validate_scrape_output import validate_positive_prices
from scripts.validate_community_scrape_output import validate_markets_and_prices


def unusual(item=10, price=100, **overrides):
    return dict(defindex=item, effect_id=6, item_name=f"Hat {item}",
                scrape_timestamp="2026-09-09T01:00:00", bp_price_ref=price,
                bp_price_keys="2 keys", slot="misc", **overrides)


def community(**overrides):
    row = dict(item_name="Hat", quality="Unique", craftable=True, item_type="Cosmetic",
               scrape_timestamp="2026-09-09T01:00:00", price_ref=100, key_price_ref=50,
               price_text="2 keys", usd_price=None, stats_url=None)
    row.update(overrides)
    return row


class CleaningQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw.csv"
        self.output = self.root / "cleaned_2026-09-09_01-00-00.csv"

    def save(self, rows):
        pd.DataFrame(rows).to_csv(self.raw, index=False)

    def report(self):
        return json.loads((self.root / "quality" / f"{self.output.stem}.quality.json").read_text())

    def test_raw_is_immutable_and_missing_zero_infinity_are_audited(self):
        self.save([unusual(10), unusual(11, None), unusual(12, 0), unusual(13, math.inf)])
        before = self.raw.read_bytes()
        result = clean_data(self.raw, self.output, 50)
        self.assertEqual(self.raw.read_bytes(), before)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0].key_price_ref, 50)
        self.assertEqual(self.report()["raw_price_status_counts"],
                         {"priced": 1, "missing": 1, "zero": 1, "invalid": 1})
        self.assertTrue(verify_quality_report(self.raw, self.output, 4, 1))
        self.output.write_text("tampered")
        with self.assertRaisesRegex(ValueError, "does not match"):
            verify_quality_report(self.raw, self.output, 4, 1)

    def test_conflicting_duplicates_are_quarantined(self):
        self.save([unusual(10, 100), unusual(10, 200), unusual(11)])
        result = clean_data(self.raw, self.output, 50)
        self.assertEqual(result.defindex.tolist(), [11])
        self.assertEqual(self.report()["rejection_counts"], {"conflicting_duplicate": 2})

    def test_identical_duplicates_are_collapsed_and_counted(self):
        self.save([unusual(), unusual()])
        self.assertEqual(len(clean_data(self.raw, self.output, 50)), 1)
        self.assertEqual(self.report()["rejection_counts"], {"duplicate_observation": 1})

    def test_rejected_only_snapshot_still_writes_report(self):
        self.save([unusual(price=0)])
        self.assertEqual(len(clean_data(self.raw, self.output, 50)), 0)
        self.assertEqual(self.report()["rejected_rows"], 1)

    def test_large_change_flagged_without_removal_and_absence_is_separate(self):
        previous = self.root / "cleaned_2026-09-08_01-00-00.csv"
        self.save([unusual(10), unusual(11), unusual(12)])
        clean_data(self.raw, previous, 50)
        self.save([unusual(10, 200), unusual(11, 0)])
        result = clean_data(self.raw, self.output, 50)
        self.assertEqual(len(result), 1)
        self.assertIn("large_price_change", result.iloc[0].quality_flags)
        comparison = self.report()["comparison"]
        self.assertEqual(len(comparison["absent_market_ids"]), 1)
        self.assertEqual(len(comparison["observed_but_rejected_market_ids"]), 1)
        self.assertEqual(comparison["comparable_markets"], 1)

    def test_api_source_range_and_update_are_preserved(self):
        self.save([unusual(source_value=1.123456789, source_value_high=2.123456789,
                           source_currency="keys", source_last_update=1700000000)])
        result = clean_data(self.raw, self.output, 50)
        self.assertEqual(result.iloc[0].source_price_low, 1.123456789)
        self.assertEqual(result.iloc[0].source_updated_at, "2023-11-14T22:13:20+00:00")
        self.assertNotIn("source_update_unknown", result.iloc[0].quality_flags)

    def test_range_parser_does_not_invent_positive_prices(self):
        for bad in ["-2 keys", "5-2 keys", "1 hat", "NaN keys", "2 keys extra", "1-2-3 keys"]:
            self.assertTrue(math.isnan(parse_price(bad)[0]), bad)
        self.assertEqual(parse_price("1,000-1,200 keys"), (1000, 1200, "keys"))

    def test_community_rejects_unknown_craftability_and_infinite_rate(self):
        self.save([community(), community(item_name="Unknown", craftable=None),
                   community(item_name="Infinite", key_price_ref=math.inf)])
        result, _ = clean_community_prices(self.raw, self.output)
        self.assertEqual(len(result), 1)
        self.assertEqual(self.report()["rejected_rows"], 2)

    def test_community_conflicts_are_not_selected_by_row_order(self):
        self.save([community(), community(price_text="3 keys")])
        result, _ = clean_community_prices(self.raw, self.output)
        self.assertTrue(result.empty)
        self.assertEqual(self.report()["rejection_counts"], {"conflicting_duplicate": 2})

    def test_backfill_preserves_raw_bytes_and_marks_approximation(self):
        row = community()
        del row["key_price_ref"]
        self.save([row])
        before = self.raw.read_bytes()
        result, _ = backfill_key_price(self.raw, 50, self.output)
        self.assertEqual(before, self.raw.read_bytes())
        self.assertIn("approximate_key_rate", result.iloc[0].quality_flags)

    def test_identity_normalizes_text_but_preserves_variants(self):
        first = market_id(community(item_name="  Team   Captain  "), "community")
        self.assertEqual(first, market_id(community(item_name="Team Captain"), "community"))
        self.assertNotEqual(first, market_id(community(item_name="Team Captain", craftable=False), "community"))
        self.assertNotEqual(first, market_id(community(item_name="Team Captain #1"), "community"))

    def test_validators_reject_nonfinite_prices(self):
        for value in ["nan", "inf", "-inf"]:
            with self.assertRaisesRegex(ValueError, "invalid processed prices"):
                validate_positive_prices(self.output, [{"bp_price_keys_equivalent": value}])
            row = dict(item_name="Hat", quality="Unique", craftable="true", price_ref=value,
                       key_price_ref="50", price_keys_equivalent="2")
            with self.assertRaisesRegex(ValueError, "invalid processed prices"):
                validate_markets_and_prices(self.output, [row])

    def test_cannot_overwrite_raw_as_output(self):
        self.save([unusual()])
        before = self.raw.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            clean_data(self.raw, self.raw, 50)
        self.assertEqual(before, self.raw.read_bytes())


if __name__ == "__main__":
    unittest.main()
