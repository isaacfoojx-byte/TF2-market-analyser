"""Read-only queries used by analysis code and a future web API."""

from __future__ import annotations

import sqlite3


def market_history(connection: sqlite3.Connection, stable_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT collected_at, price_keys, price_ref, key_price_ref,
               source_updated_at, quality_flags, source_file
        FROM market_price_history
        WHERE stable_id = ?
        ORDER BY collected_at
        """,
        (stable_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def latest_markets(
    connection: sqlite3.Connection, dataset: str, limit: int = 100
) -> list[dict]:
    if dataset not in {"unusual", "community"}:
        raise ValueError(f"Unsupported dataset {dataset!r}")
    if limit < 1 or limit > 10_000:
        raise ValueError("limit must be between 1 and 10,000")
    rows = connection.execute(
        """
        SELECT m.stable_id, m.item_name, m.effect_name, m.quality, m.craftable,
               s.collected_at, o.price_keys, o.price_ref, o.source_updated_at
        FROM snapshots AS s
        JOIN price_observations AS o USING (snapshot_id)
        JOIN markets AS m USING (market_id)
        WHERE s.snapshot_id = (
            SELECT snapshot_id FROM snapshots
            WHERE dataset = ? ORDER BY collected_at DESC LIMIT 1
        )
        ORDER BY m.item_name, m.effect_name, m.quality
        LIMIT ?
        """,
        (dataset, limit),
    ).fetchall()
    return [dict(row) for row in rows]
