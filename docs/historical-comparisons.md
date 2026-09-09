# Historical guide-price comparisons

The latest dashboard and custom-period comparisons now share
`analytics/comparison.py`. This works with existing snapshots and the additive
provenance columns introduced by cleaning version 2.0.

## Compare the same market

Unusual rows join by definition ID and effect ID (in the collector's tradable,
craftable scope); name changes do not create false entrants. Community rows use
the cleaner's normalized name/quality/craftability identity, including the
priceindex suffix in indexed names. Genuine community renames still need aliases.

An outer join preserves **Entered coverage**, **Left coverage**, and
**Unpriced or ambiguous** rows. Only markets with finite positive prices at both
endpoints receive a price change. Missing prices are never replaced with zero.
These are processed-snapshot coverage changes, not proof of a sale, new supply,
or removal from the economy. Cleaning can also change coverage; inspect the
cleaning reports for missing versus rejected raw observations.

Repeated identical prices count once per market. Conflicting duplicate prices
make that market incomparable, rather than averaging incompatible values.
`observation_count` describes CSV observations only. There is no listing-count
or liquidity estimate in this comparison, and the website's opportunity detector
has been replaced by a rising guide-price list without a trading score.

Matched percentage summaries give each comparable market equal weight. Unchanged
markets remain in the denominator. The direction score is
`50 + 50 * (rising - falling) / comparable_count`; an entirely unchanged pair
scores 50. It describes guide-price direction, not trader sentiment. Scores at
least 60 are labelled Rising; at most 40 Falling; otherwise Mixed / steady.

Catalog average/median charts remain available but are labelled as composition
sensitive: their item mix can change. Matched endpoint metrics are presented
separately. Endpoint movement does not establish a sustained trend in between.

## Price and key-rate attribution

For source prices quoted in refined metal, using original midpoint values P and
captured rates R (ref per key):

- Item component in keys = `(P_new - P_old) / R_old`.
- Rate component in keys = total observed key change minus the item component.

This applies the item change at the old rate first, then the rate change. It is
an explicit arithmetic convention, not causal attribution. For prices originally
quoted in keys, item movement is the key-price change and rate movement is zero.

Components are available only for matching source currencies, usable original
ranges, and consistent normalized prices; ref quotes also require both rates.
Derived legacy key displays and approximate backfilled rates are excluded.
Unknown currency, changed denomination, conflicting metadata, or unavailable
rates leave attribution unavailable. No rate is reverse-engineered from prices.

## Freshness and consistency

Source age is measured at collection from `source_updated_at`; it is separate
from website/data freshness. Missing, future, or flagged timezone-unknown values
have unknown age. Older captures generally cannot support this metric.

The 30-day source-age threshold is a review heuristic. Market-direction evidence
is High only with at least 100 comparable markets, 80% overlap with the union,
and 80% known source ages within 30 days; Medium requires at least 25 comparable
markets and 50% overlap, otherwise Low. This is evidence coverage, not investment
confidence or liquidity. Source ages and unavailable attribution remain visible.

Item histories retain gaps for missing/unpriced observations. Returns use only
adjacent saved observations with prices; they are not forward-filled across gaps.
The UI reports rising, falling, and unchanged adjacent intervals, missing captures,
and distinct known source-update timestamps. Gaps between capture dates are
reported separately; intervals are not assumed to be daily. A repeated old guide
value is not treated as an independent source revision.

Trend evidence cannot be High from capture count alone: it also requires five
known distinct source updates, no missing captures, and 80% source ages within
30 days. Historical data without source timestamps remains limited evidence.

## Validation

Unit tests cover renames, changing catalog composition, unchanged denominators,
missing prices, conflicting duplicates, native-key prices, ref/key-rate changes,
source age, and gaps. Streamlit AppTest checks the affected pages against the
saved datasets. No historical CSVs or live deployment are modified by this change.
