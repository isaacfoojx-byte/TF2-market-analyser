"""Benchmark the read queries that drive the TFAnalytics website and API."""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Callable

from database.create_database import DEFAULT_DB_PATH, connect_database
from database.queries import (
    latest_comparison_summary,
    latest_markets,
    market_history,
    search_markets,
    snapshot_overview,
)


def timed_query(function: Callable[[], object], repeats: int) -> dict:
    function()  # Warm the database and OS page caches before measuring.
    durations = []
    result = None
    for _ in range(repeats):
        started = time.perf_counter()
        result = function()
        durations.append((time.perf_counter() - started) * 1000)
    result_count = len(result) if isinstance(result, list) else int(result is not None)
    return {
        "median_ms": round(statistics.median(durations), 3),
        "slowest_ms": round(max(durations), 3),
        "result_count": result_count,
    }


def representative_market(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        """
        SELECT m.stable_id
        FROM price_observations AS o
        JOIN markets AS m USING (market_id)
        GROUP BY o.market_id
        ORDER BY COUNT(*) DESC, m.stable_id
        LIMIT 1
        """
    ).fetchone()
    return row["stable_id"] if row else None


def benchmark_database(path: Path, repeats: int = 7) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"Database does not exist: {path}. Build it with "
            "python -m database.import_data --processed-root data/processed"
        )
    with connect_database(path) as connection:
        stable_id = representative_market(connection)
        query_results = {
            "snapshot_overview": timed_query(
                lambda: snapshot_overview(connection), repeats
            ),
            "latest_unusual_page": timed_query(
                lambda: latest_markets(connection, "unusual", 100), repeats
            ),
            "market_search": timed_query(
                lambda: search_markets(connection, "unusual", "hat", 25), repeats
            ),
            "latest_unusual_comparison": timed_query(
                lambda: latest_comparison_summary(connection, "unusual"), repeats
            ),
        }
        if stable_id:
            query_results["representative_market_history"] = timed_query(
                lambda: market_history(connection, stable_id), repeats
            )
        counts = dict(
            connection.execute(
                """
                SELECT (SELECT COUNT(*) FROM snapshots) AS snapshots,
                       (SELECT COUNT(*) FROM markets) AS markets,
                       (SELECT COUNT(*) FROM market_presence) AS market_presence,
                       (SELECT COUNT(*) FROM price_observations) AS observations
                """
            ).fetchone()
        )
    return {
        "database": str(path.resolve()),
        "database_bytes": path.stat().st_size,
        "repeats": repeats,
        "representative_stable_id": stable_id,
        "counts": counts,
        "queries": query_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    result = benchmark_database(args.database, args.repeats)
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
