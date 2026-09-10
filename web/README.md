# TFAnalytics web app

This is the Next.js replacement path for the Streamlit interface. It currently
provides market search, an item-detail history page, and JSON endpoints backed by
the normalized historical database.

## Local development

Build `database/market_v2.db` from the repository root, then start the site:

```bash
python -m database.import_data --processed-root data/processed
cd web
pnpm install
pnpm dev
```

The default local database is `../database/market_v2.db`. Override it with
`TFANALYTICS_SQLITE_PATH` when needed.

## Routes

- `/` searches or lists the latest markets.
- `/markets/[stableId]` shows one market's recorded price history.
- `/api/markets?dataset=unusual&q=hat&limit=30` returns catalog results.
- `/api/markets/[stableId]/history` returns metadata and observations.

When `DATABASE_URL` is set, the server uses pooled PostgreSQL instead of local
SQLite. Keep that variable server-side; do not prefix it with `NEXT_PUBLIC_`.

After provisioning an empty managed PostgreSQL database, migrate the archive from
the repository root:

```bash
python -m database.migrate_to_postgres
```

Daily jobs publish one validated snapshot idempotently with:

```bash
python -m database.import_postgres path/to/cleaned_snapshot.csv --dataset unusual
python -m database.import_postgres path/to/community_snapshot.csv --dataset community
```

Set the GitHub Actions `DATABASE_URL` secret to the database's direct,
unpooled connection string. The importer validates the quality report, performs
all writes in one transaction, verifies priced and unpriced row counts, and
reports database usage. It emits a GitHub Actions warning at 85% of 512 MiB;
override those assumptions with `DATABASE_SIZE_WARNING_PERCENT` and
`DATABASE_SIZE_LIMIT_MIB` if the database plan changes.

The migration refuses a non-empty target, copies all normalized tables in one
transaction, updates identity sequences, and verifies every row count before it
commits.
