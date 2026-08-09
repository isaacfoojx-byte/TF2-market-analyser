import unittest
from datetime import datetime

from scraper.community_api import build_community_rows


class CommunityApiTests(unittest.TestCase):
    def test_builds_non_unusual_rows_and_excludes_unusuals(self):
        payload = {
            "success": 1,
            "items": {
                "Mann Co. Supply Crate Key": {
                    "prices": {
                        "6": {
                            "Tradable": {
                                "Craftable": {
                                    "0": {
                                        "currency": "metal",
                                        "value": 90,
                                        "value_high": 92,
                                        "value_raw": 90,
                                        "value_raw_high": 92,
                                    }
                                }
                            }
                        }
                    }
                },
                "Example Hat": {
                    "item_type": "Cosmetic",
                    "prices": {
                        "5": {
                            "Tradable": {
                                "Craftable": {
                                    "13": {"currency": "keys", "value": 2}
                                }
                            }
                        },
                        "6": {
                            "Tradable": {
                                "Craftable": {
                                    "114": {
                                        "currency": "metal",
                                        "value": 3,
                                        "value_high": 4,
                                    }
                                }
                            }
                        },
                        "11": {
                            "Tradable": {
                                "Non-Craftable": {
                                    "0": {"currency": "keys", "value": 1.5}
                                }
                            }
                        },
                    },
                },
            },
        }

        rows = build_community_rows(payload, datetime(2026, 8, 9, 12, 0, 0))
        example_rows = rows.loc[rows["item_name"].str.startswith("Example Hat")]

        self.assertEqual(set(example_rows["quality"]), {"Unique", "Strange"})
        self.assertNotIn("Unusual", set(rows["quality"]))
        unique = example_rows.loc[example_rows["quality"].eq("Unique")].iloc[0]
        strange = example_rows.loc[example_rows["quality"].eq("Strange")].iloc[0]
        self.assertEqual(unique["price_text"], "3–4 ref")
        self.assertEqual(unique["item_name"], "Example Hat #114")
        self.assertEqual(unique["price_ref"], 3.5)
        self.assertFalse(bool(strange["craftable"]))
        self.assertEqual(strange["price_ref"], 136.5)


if __name__ == "__main__":
    unittest.main()
