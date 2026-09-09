# Snapshot cleaning and quality reports

The cleaners now use cleaning version `2.0`. They write derived CSVs and reports;
raw files are never rewritten by cleaning, including key-rate backfills. Existing
historical snapshots are not automatically reprocessed. Core price and selector
columns remain available for the website and Sheets exporter; provenance and
quality columns are additive.

## Row rules

- Accept finite, positive normalized prices and conversion rates. Blank, zero,
  negative, malformed, NaN, and infinite inputs are distinct in the raw row audit.
  For community data, a valid captured display/API price can replace an absent
  refined tooltip; the original tooltip remains in the raw capture and audit.
- Require an identity and valid collection timestamp. A snapshot with multiple
  valid collection timestamps fails cleaning. Missing required columns also fail
  early. These structural failures do not produce row-level reports.
- Collapse identical duplicate price observations, recording the redundant rows.
  Quarantine every conflicting duplicate instead of choosing a price by row order.
- Reject malformed, negative, reversed, or unsupported source ranges. Keep original
  source fields when available; older Unusual key-display ranges are explicitly
  marked as derived rather than misrepresented as the original currency.
- Keep large price movements. A change of at least 50% against the prior accepted
  price gets `large_price_change`. Set `change_threshold` / `--change-threshold`
  to another positive fraction if needed. This is a review heuristic, not proof
  of a data error, trading opportunity, or movement in actual sale prices.

Missing/unpriced rows are quarantined from the priced analysis CSV and retained
in the row audit. No price is forward-filled. The comparison report separates
markets absent from the raw capture from markets observed but rejected by cleaning.
An absent entry does not imply a zero price or a delisted item.

## Identity and provenance

Unusual market IDs encode defindex, effect, and the current collector's fixed
tradable/craftable scope. Community IDs hash normalized item name, quality, and
craftability in the tradable scope. API priceindex variants already have a suffix
in the stored item name and stay separate. Community identity is explicitly
`name_based_identity`: legacy snapshots do not have reliable numeric item IDs,
so a genuine rename needs a future alias mapping. This schema does not claim to
identify every possible inventory attribute beyond the price guide's scope.

`key_price_ref` records the exact conversion rate used; `key_rate_source` records
whether it was captured, supplied, or supplied as an approximation. Backfilling
with a manual rate adds `approximate_key_rate` and leaves the raw input unchanged.

New API captures retain `source_value`, `source_value_high`, `source_currency`,
and optional `source_last_update`. Cleaned data includes the original range/unit,
`source_updated_at`, and `collected_at` separately. An unavailable source timestamp
is blank with `source_update_unknown`; collection time is never substituted for it.
New scheduled API captures use explicit UTC. Legacy naive collection timestamps
are flagged `collection_timezone_unknown`; their timezone is not guessed for
source-time comparisons. Invalid API entries excluded before raw CSV creation
are outside this cleaner's audit scope.

## Outputs and publication

For each processed CSV, `processed/quality/` contains:

- `<snapshot>.quality.json`: cleaning version, source/output SHA-256 hashes, row
  totals, rejection/warning counts, missing fields, captured times, rates, and
  previous-snapshot comparison (including absent and rejected market IDs).
- `<snapshot>.rows.csv`: original input fields plus original row number,
  disposition, rejection reason, price status, market ID, and quality flags.

The previous snapshot is the newest earlier filename in the supplied directory;
no future snapshot is used. Duplicate or missing previous identities disable
comparison with an explicit report status. If there is no baseline, no change is
invented. Comparisons use guide prices in keys and may include key-rate effects.

Validation checks the report hashes and row accounting when rows were removed,
then applies the existing minimum-size and maximum-drop safeguards. An all-rejected
snapshot cannot pass publication. Reports do not bypass price or identity checks.
Historical files without reports keep the existing validation behavior.

Daily workflows commit JSON reports beside the corresponding processed dataset
under its `quality/` directory, and upload full row audits as 14-day workflow
artifacts, including when validation fails. The raw CSVs remain the durable source
for regenerating audits after artifacts expire. No database migration is required.

## Reprocess a copy

Choose a separate output directory when exploring older data. Use a historical
key rate supported by evidence; do not substitute today's rate for an old capture.

```bash
python -m processing.clean_data RAW_CSV OUTPUT_CSV --key-price-ref HISTORICAL_RATE --previous-processed-dir data/processed
python -m processing.community_prices RAW_CSV --output OUTPUT_CSV --previous-processed-dir data/processed/non_unusual
```

For community snapshots missing their conversion rate, add `--key-price-ref` to
supply an explicitly approximate rate. Run the appropriate snapshot validator
before publishing derived results. Review rejected records and large-change flags
rather than loosening validation just to make a run pass.
