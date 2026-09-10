"""Incrementally publish one cleaned snapshot to the hosted PostgreSQL database."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from database.import_data import (
    REQUIRED_COLUMNS,
    ImportResult,
    file_sha256,
    finite_number,
    has_usable_price,
    load_quality_report,
    market_values,
    observation_values,
    optional_text,
    read_snapshot,
    row_stable_id,
)


MARKET_COLUMNS = (
    "stable_id", "dataset", "defindex", "effect_id", "item_name",
    "effect_name", "quality", "craftable", "item_type", "slot", "summary",
    "first_seen_at", "last_seen_at",
)
OBSERVATION_COLUMNS = (
    "snapshot_id", "market_id", "price_ref", "price_keys", "price_usd",
    "key_price_ref", "source_price_low", "source_price_high",
    "source_price_unit", "source_updated_at", "source_price_provenance",
    "key_rate_source", "price_is_range", "quality_flags", "raw_row_number",
)

DEFAULT_DATABASE_LIMIT_MIB = 512
DEFAULT_DATABASE_WARNING_PERCENT = 85


def prepare_snapshot(path: Path, dataset: str) -> tuple[list[tuple], str, dict | None, str]:
    """Validate and normalize a CSV before opening a database transaction."""
    rows, collected_at = read_snapshot(path, dataset)
    source_hash = file_sha256(path)
    report, validation_status = load_quality_report(path, source_hash)
    if report is not None and report.get("accepted_rows") != len(rows):
        raise ValueError("Quality report accepted_rows does not match the CSV")

    prepared: list[tuple] = []
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        try:
            identity = row_stable_id(row, dataset)
            if identity in seen:
                raise ValueError(f"Duplicate market identity {identity}")
            seen.add(identity)
            observation = observation_values(row, dataset) if has_usable_price(row, dataset) else None
            raw_row = finite_number(row, "raw_row_number", positive=True)
            prepared.append((
                identity,
                market_values(row, dataset, collected_at),
                observation,
                optional_text(row, "quality_flags"),
                int(raw_row) if raw_row is not None else None,
            ))
        except ValueError as error:
            raise ValueError(f"{path}:{row_number}: {error}") from error
    return prepared, collected_at, report, validation_status


def _boolean_market(values: tuple) -> tuple:
    mutable = list(values)
    mutable[7] = bool(mutable[7])
    return tuple(mutable)


def _boolean_observation(values: tuple) -> tuple:
    mutable = list(values)
    if mutable[10] is not None:
        mutable[10] = bool(mutable[10])
    return tuple(mutable)


def import_snapshot(database_url: str, path: str | Path, dataset: str) -> ImportResult:
    """Atomically insert one snapshot; content-identical reruns are no-ops."""
    if dataset not in REQUIRED_COLUMNS:
        raise ValueError(f"Unsupported dataset {dataset!r}")
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as error:
        raise RuntimeError('Install PostgreSQL support with pip install "psycopg[binary]==3.3.5"') from error

    source_path = Path(path)
    source_hash = file_sha256(source_path)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            identical = cursor.execute(
                "SELECT snapshot_id,market_count,priced_observation_count "
                "FROM snapshots WHERE dataset=%s AND source_sha256=%s",
                (dataset, source_hash),
            ).fetchone()
            if identical:
                return ImportResult(source_path.name, dataset, *identical, "unchanged")

        prepared, collected_at, report, validation_status = prepare_snapshot(source_path, dataset)
        expected_priced = sum(item[2] is not None for item in prepared)
        imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

        with connection.transaction(), connection.cursor() as cursor:
            existing = cursor.execute(
                "SELECT snapshot_id,source_sha256,market_count,priced_observation_count "
                "FROM snapshots WHERE dataset=%s AND collected_at=%s FOR UPDATE",
                (dataset, collected_at),
            ).fetchone()
            if existing:
                if existing[1] != source_hash:
                    raise ValueError(f"A different {dataset} snapshot already exists for {collected_at}")
                return ImportResult(source_path.name, dataset, existing[0], existing[2], existing[3], "unchanged")

            snapshot_id = cursor.execute(
                """
                INSERT INTO snapshots (
                    dataset,collected_at,source_file,source_sha256,cleaning_version,
                    validation_status,imported_at,market_count,
                    priced_observation_count,quality_report_json
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING snapshot_id
                """,
                (
                    dataset, collected_at, source_path.as_posix(), source_hash,
                    report.get("cleaning_version") if report else None,
                    validation_status, imported_at, len(prepared), expected_priced,
                    Jsonb(report) if report else None,
                ),
            ).fetchone()[0]

            names = ",".join(MARKET_COLUMNS)
            cursor.execute(
                f"CREATE TEMP TABLE staged_markets ON COMMIT DROP AS "
                f"SELECT {names} FROM markets WITH NO DATA"
            )
            with cursor.copy(f"COPY staged_markets ({names}) FROM STDIN") as copy:
                for _, market, _, _, _ in prepared:
                    copy.write_row(_boolean_market(market))
            cursor.execute(f"""
                INSERT INTO markets ({names}) SELECT {names} FROM staged_markets
                ON CONFLICT(stable_id) DO UPDATE SET
                    item_name=CASE WHEN EXCLUDED.last_seen_at >= markets.last_seen_at THEN EXCLUDED.item_name ELSE markets.item_name END,
                    effect_name=CASE WHEN EXCLUDED.last_seen_at >= markets.last_seen_at THEN COALESCE(EXCLUDED.effect_name,markets.effect_name) ELSE markets.effect_name END,
                    item_type=CASE WHEN EXCLUDED.last_seen_at >= markets.last_seen_at THEN COALESCE(EXCLUDED.item_type,markets.item_type) ELSE markets.item_type END,
                    slot=CASE WHEN EXCLUDED.last_seen_at >= markets.last_seen_at THEN COALESCE(EXCLUDED.slot,markets.slot) ELSE markets.slot END,
                    summary=CASE WHEN EXCLUDED.last_seen_at >= markets.last_seen_at THEN COALESCE(EXCLUDED.summary,markets.summary) ELSE markets.summary END,
                    first_seen_at=LEAST(markets.first_seen_at,EXCLUDED.first_seen_at),
                    last_seen_at=GREATEST(markets.last_seen_at,EXCLUDED.last_seen_at)
            """)
            market_rows = {
                stable_id: (market_id, market_dataset)
                for stable_id, market_id, market_dataset in cursor.execute(
                    "SELECT m.stable_id,m.market_id,m.dataset FROM markets m "
                    "JOIN staged_markets s USING(stable_id)"
                )
            }

            observations: list[tuple] = []
            unpriced: list[tuple] = []
            for identity, _, observation, quality_flags, raw_row_number in prepared:
                market_id, market_dataset = market_rows[identity]
                if market_dataset != dataset:
                    raise ValueError(f"Market identity {identity} changed dataset")
                if observation is None:
                    unpriced.append((snapshot_id, market_id, quality_flags, raw_row_number))
                else:
                    observations.append((snapshot_id, market_id, *_boolean_observation(observation)))

            with cursor.copy(
                f"COPY price_observations ({','.join(OBSERVATION_COLUMNS)}) FROM STDIN"
            ) as copy:
                for row in observations:
                    copy.write_row(row)
            with cursor.copy(
                "COPY unpriced_market_presence "
                "(snapshot_id,market_id,quality_flags,raw_row_number) FROM STDIN"
            ) as copy:
                for row in unpriced:
                    copy.write_row(row)

            if report:
                issues = [
                    (snapshot_id, code, kind, int(count))
                    for kind, field in (("warning", "warning_counts"), ("rejection", "rejection_counts"))
                    for code, count in report.get(field, {}).items()
                ]
                if issues:
                    with cursor.copy(
                        "COPY snapshot_quality_issues "
                        "(snapshot_id,issue_code,issue_kind,affected_rows) FROM STDIN"
                    ) as copy:
                        for issue in issues:
                            copy.write_row(issue)

            actual_priced = cursor.execute(
                "SELECT COUNT(*) FROM price_observations WHERE snapshot_id=%s",
                (snapshot_id,),
            ).fetchone()[0]
            actual_unpriced = cursor.execute(
                "SELECT COUNT(*) FROM unpriced_market_presence WHERE snapshot_id=%s",
                (snapshot_id,),
            ).fetchone()[0]
            if actual_priced != expected_priced or actual_priced + actual_unpriced != len(prepared):
                raise RuntimeError(
                    "Snapshot verification failed: "
                    f"expected {len(prepared)} markets/{expected_priced} priced, got "
                    f"{actual_priced + actual_unpriced}/{actual_priced}"
                )

    return ImportResult(source_path.name, dataset, snapshot_id, len(prepared), expected_priced, "imported")


def database_usage(database_url: str) -> tuple[int, float]:
    """Return PostgreSQL database size in bytes and MiB."""
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError('Install PostgreSQL support with pip install "psycopg[binary]==3.3.5"') from error
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        size_bytes = cursor.execute(
            "SELECT pg_database_size(current_database())"
        ).fetchone()[0]
    return size_bytes, size_bytes / 1024 / 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--dataset", required=True, choices=sorted(REQUIRED_COLUMNS))
    parser.add_argument("--database-url-env", default="DATABASE_URL")
    args = parser.parse_args()
    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        parser.error(f"{args.database_url_env} is not set")
    result = import_snapshot(database_url, args.path, args.dataset)
    print(
        f"PostgreSQL snapshot {result.action}: {result.source_file}; "
        f"{result.markets:,} markets, {result.priced_observations:,} priced observations verified."
    )
    size_bytes, size_mib = database_usage(database_url)
    limit_mib = float(os.environ.get("DATABASE_SIZE_LIMIT_MIB", DEFAULT_DATABASE_LIMIT_MIB))
    warning_percent = float(
        os.environ.get("DATABASE_SIZE_WARNING_PERCENT", DEFAULT_DATABASE_WARNING_PERCENT)
    )
    used_percent = size_bytes / (limit_mib * 1024 * 1024) * 100
    print(f"PostgreSQL database size: {size_mib:,.1f} MiB ({used_percent:.1f}% of {limit_mib:g} MiB).")
    if os.environ.get("GITHUB_ACTIONS") == "true" and used_percent >= warning_percent:
        print(
            f"::warning::PostgreSQL database is {used_percent:.1f}% full "
            f"({size_mib:,.1f} of {limit_mib:g} MiB)."
        )


if __name__ == "__main__":
    main()
