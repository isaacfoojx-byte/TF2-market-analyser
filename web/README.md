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
