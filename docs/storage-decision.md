# Storage decision

## Decision

Use each store for one job:

- Keep processed CSV snapshots as the recoverable source archive.
- Use the generated SQLite database for local analysis, data-quality work, and
  repeatable benchmarks.
- Use managed PostgreSQL when the Vercel site starts serving arbitrary item
  histories through API routes.
- Generate small static JSON responses for public overview pages when a daily
  build is enough. Do not export the complete history as frontend JSON.

This matches the next intended feature: a public item-detail page that can search
roughly 49,000 markets and retrieve one market's history from about 2.5 million
observations. PostgreSQL has the same relational shape as the normalized SQLite
schema, supports the required joins and constraints, and can be shared safely by
multiple serverless function instances.

The current CSV archive is about 718 MB and a full SQLite rebuild is about 321 MB.
Shipping either complete dataset to every browser or Vercel deployment would make
the website carry data it does not need for each request.

## Query contract

`database.queries` is the first storage boundary. It contains parameterized
operations for:

- dataset and snapshot overview;
- a page of latest markets;
- catalog search;
- one stable market's price history; and
- comparison of the latest two snapshots.

UI and future API code should call operations with this shape instead of embedding
SQL throughout route handlers. The PostgreSQL implementation can then preserve the
responses while changing connection and placeholder syntax.

## Measure before provisioning

Build the local database, then benchmark the real read patterns:

```bash
python -m database.import_data --processed-root data/processed
python -m scripts.benchmark_storage
```

The benchmark reports the database size, row counts, and warm median/slowest times
for overview, latest-list, search, comparison, and item-history queries. Save a
machine-readable baseline when needed:

```bash
python -m scripts.benchmark_storage --output artifacts/storage-benchmark.json
```

Local timings are not predictions of network latency. They show query shape,
indexing problems, and growth over time. Once PostgreSQL is connected, run the same
logical operations against a staging copy and measure end-to-end API latency.

Baseline from the 2026-09-10 local rebuild (seven warm runs per query):

| Query | Median |
| --- | ---: |
| Snapshot overview | 0.022 ms |
| Search for `hat`, first 25 results | 0.157 ms |
| One representative 56-point item history | 0.271 ms |
| Latest unusual catalog, first 100 results | 11.988 ms |
| Compare all shared markets in the latest unusual snapshots | 40.633 ms |

That rebuild contained 90 snapshots, 48,777 stable markets, 2,501,663 presence
records, and 2,494,442 priced observations. These results show that the current
schema and indexes are adequate for the planned reads. PostgreSQL is a deployment
and shared-durability choice at this scale, not a response to slow local queries.

## Migration trigger

Provision PostgreSQL as part of the Vercel phase that adds the item-history API.
It is unnecessary for a static landing page. It becomes necessary when any deployed
feature needs shared dynamic reads or writes, including item history, watchlists,
accounts, or scraper-driven updates that must appear without a new site build.

Use a pooled serverless connection supplied by the selected provider, put the
database in the same region as the Vercel Functions, and keep credentials in
environment variables. Vercel's current
[Marketplace storage guidance](https://vercel.com/docs/marketplace-storage)
lists managed Postgres providers and recommends both pooling and placing data near
Functions. Vercel's former first-party Postgres product has moved to Marketplace
providers, as described in its
[Postgres documentation](https://vercel.com/docs/postgres). The daily importer
should remain one controlled job and write each snapshot in a transaction.

Object storage can be added later for immutable CSV backups if Git repository size
or checkout time becomes painful. Redis, document databases, and vector databases
do not improve the current relational price-history queries and should not be added
for this phase.
