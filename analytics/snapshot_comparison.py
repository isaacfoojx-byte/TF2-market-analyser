import pandas as pd

from utils import (
    get_latest_pair,
    load_data
)

old_file, new_file = get_latest_pair()

old_df, old_priced = load_data(old_file)
new_df, new_priced = load_data(new_file)

comparison = old_priced.merge(
    new_priced,
    on=["effect_id", "defindex"],
    suffixes=("_old", "_new"),
    how="outer",
    indicator=True
)

comparison["status"] = "Unchanged"

comparison.loc[
    comparison["_merge"] == "right_only",
    "status"
] = "New Listing"

comparison.loc[
    comparison["_merge"] == "left_only",
    "status"
] = "Removed"

comparison.loc[
    comparison["key_change"] > 0,
    "status"
] = "Price Increased"

comparison.loc[
    comparison["key_change"] < 0,
    "status"
] = "Price Decreased"

unchanged = comparison[
    comparison["_merge"] == "both"
]

new_items = comparison[
    comparison["_merge"] == "right_only"
]

removed_items = comparison[
    comparison["_merge"] == "left_only"
]

comparison["key_change"] = (
    comparison["bp_price_keys_equivalent_new"]
    - comparison["bp_price_keys_equivalent_old"]
)

comparison["percent_change"] = (
    comparison["key_change"]
    / comparison["bp_price_keys_equivalent_old"]
) * 100

price_changed = comparison[
    comparison["key_change"] != 0
]

comparison.nlargest(
    10,
    "key_change"
)

comparison.nsmallest(
    10,
    "key_change"
)

comparison.nlargest(
    10,
    "percent_change"
)