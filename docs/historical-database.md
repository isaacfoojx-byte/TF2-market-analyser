# Historical database

TFAnalytics now has a normalized SQLite store for local analysis and API
prototyping. The processed CSV snapshots remain the durable source archive. The
database is a rebuildable index of those files.

The old tracked `database/market.db` is preserved as a legacy prototype. New code
uses the ignored `database/market_v2.db`, so local imports do not create large Git
commits.

## Data model

- `snapshots` records one immutable import per dataset and collection time,
  including its SHA-256 hash, cleaning version, validation status, and full quality
  report when available.
- `markets` stores stable identities and descriptive attributes. Unusual identity
  uses defindex and effect ID. Community identity uses the current normalized
  name, quality, and craftability scheme.
- `market_presence` records whether a market was present with a usable price or was
  present but unpriced. This preserves legacy missing prices without inventing zero.
- `price_observations` stores one usable price for each `(snapshot, market)` pair. Database
  constraints reject duplicate observations, non-positive prices, invalid ranges,
  and broken references.
- `snapshot_quality_issues` makes aggregate cleaning warnings and rejections
  queryable.
- `market_price_history` is a read-only view for the common item-history query.

Market names and metadata update when newer information is imported. `first_seen_at`
and `last_seen_at` preserve the observed time range. Importing files out of order is
supported.

## Build and import

Create an empty database and import every processed snapshot:

```bash
python -m database.create_database
python -m database.import_data --processed-root data/processed
```

Import one explicit file:

```bash
python -m database.import_data data/processed/cleaned_TIMESTAMP.csv --dataset unusual
```

The import is transactional per snapshot. A bad row rolls back that entire
snapshot. Importing the same file again is a verified no-op. A different file with
the same dataset and collection timestamp is rejected instead of silently replacing
history.

A complete rebuild currently stores about 2.5 million priced observations in a
roughly 320 MB SQLite file. The generated file is ignored by Git. Re-importing the
same archive uses content hashes to skip rows that are already present.

Files with matching cleaning reports are marked `validated`; older snapshots
without reports are retained as `legacy_unverified`. A report with a mismatched
content hash is rejected. This label describes pipeline verification, not market
price accuracy.

## Query examples

```sql
SELECT dataset, COUNT(*) AS snapshots,
       SUM(market_count) AS markets,
       SUM(priced_observation_count) AS priced_observations
FROM snapshots
GROUP BY dataset;

SELECT collected_at, price_keys, key_price_ref, source_updated_at
FROM market_price_history
WHERE stable_id = 'tf2:unusual:30753:6:tradable:craftable'
ORDER BY collected_at;

SELECT issue_code, SUM(affected_rows)
FROM snapshot_quality_issues
GROUP BY issue_code
ORDER BY SUM(affected_rows) DESC;
```

`database.queries` contains parameterized helpers for latest-market and history
lookups, catalog search, snapshot overview, and period comparison. Those functions
can later sit behind API endpoints without exposing SQL or accepting arbitrary
query text from a browser. The rationale and migration triggers are recorded in
[Storage decision](storage-decision.md).

## Moving to Vercel

SQLite is appropriate for local analysis, tests, and generating static frontend
data. A Vercel function should not treat a bundled SQLite file as writable durable
storage. When the site needs live queries, accounts, or watchlists, move this schema
to managed PostgreSQL and change the connection layer. Keep the same stable IDs,
snapshot uniqueness rules, and import transaction boundaries.

Do not commit generated database files or service credentials. Do not remove the
CSV archive after a database import; it remains the recovery path if the schema or
cleaning rules change.
