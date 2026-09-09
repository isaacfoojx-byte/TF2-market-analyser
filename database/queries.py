"""Read-only queries used by analysis code and a future web API."""

from __future__ import annotations

import sqlite3


DATASETS = {"unusual", "community"}


def _validate_dataset(dataset: str) -> None:
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported dataset {dataset!r}")


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
    _validate_dataset(dataset)
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


def snapshot_overview(connection: sqlite3.Connection) -> list[dict]:
    """Return small dataset-level totals suitable for a status/API response."""

    rows = connection.execute(
        """
        SELECT dataset, COUNT(*) AS snapshot_count,
               MIN(collected_at) AS first_collected_at,
               MAX(collected_at) AS latest_collected_at,
               SUM(market_count) AS market_presence_count,
               SUM(priced_observation_count) AS priced_observation_count
        FROM snapshots
        GROUP BY dataset
        ORDER BY dataset
        """
    ).fetchall()
    return [dict(row) for row in rows]


def search_markets(
    connection: sqlite3.Connection,
    dataset: str,
    query: str,
    limit: int = 25,
) -> list[dict]:
    """Search the market catalog without exposing arbitrary SQL to callers."""

    _validate_dataset(dataset)
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    term = query.strip()
    if not term:
        return []
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = connection.execute(
        """
        SELECT stable_id, item_name, effect_name, quality, craftable,
               first_seen_at, last_seen_at
        FROM markets
        WHERE dataset = ?
          AND (item_name LIKE ? ESCAPE '\\' COLLATE NOCASE
               OR COALESCE(effect_name, '') LIKE ? ESCAPE '\\' COLLATE NOCASE)
        ORDER BY item_name, effect_name, quality
        LIMIT ?
        """,
        (dataset, f"%{escaped}%", f"%{escaped}%", limit),
    ).fetchall()
    return [dict(row) for row in rows]


def latest_comparison_summary(
    connection: sqlite3.Connection, dataset: str
) -> dict | None:
    """Compare markets shared by the latest two snapshots of one dataset."""

    _validate_dataset(dataset)
    snapshots = connection.execute(
        """
        SELECT snapshot_id, collected_at
        FROM snapshots
        WHERE dataset = ?
        ORDER BY collected_at DESC
        LIMIT 2
        """,
        (dataset,),
    ).fetchall()
    if len(snapshots) < 2:
        return None
    newer, older = snapshots
    row = connection.execute(
        """
        SELECT COUNT(*) AS shared_market_count,
               SUM(CASE WHEN new.price_keys > old.price_keys THEN 1 ELSE 0 END)
                   AS increased_count,
               SUM(CASE WHEN new.price_keys < old.price_keys THEN 1 ELSE 0 END)
                   AS decreased_count,
               SUM(CASE WHEN new.price_keys = old.price_keys THEN 1 ELSE 0 END)
                   AS unchanged_count,
               AVG((new.price_keys - old.price_keys) / old.price_keys * 100.0)
                   AS average_change_pct
        FROM price_observations AS old
        JOIN price_observations AS new USING (market_id)
        WHERE old.snapshot_id = ? AND new.snapshot_id = ?
        """,
        (older["snapshot_id"], newer["snapshot_id"]),
    ).fetchone()
    return {
        "dataset": dataset,
        "older_collected_at": older["collected_at"],
        "newer_collected_at": newer["collected_at"],
        **dict(row),
    }
