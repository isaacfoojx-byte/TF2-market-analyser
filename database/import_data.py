"""Import cleaned CSV snapshots into the normalized historical database."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from database.create_database import DEFAULT_DB_PATH, connect_database
from processing.quality import market_id as derive_market_id


REQUIRED_COLUMNS = {
    "unusual": {
        "scrape_timestamp", "defindex", "effect_id", "item_name",
        "bp_price_ref", "bp_price_keys_equivalent",
    },
    "community": {
        "scrape_timestamp", "item_name", "quality", "craftable",
        "price_ref", "price_keys_equivalent",
    },
}


@dataclass(frozen=True)
class ImportResult:
    source_file: str
    dataset: str
    snapshot_id: int
    markets: int
    priced_observations: int
    action: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("Snapshot has a blank scrape_timestamp")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
    # Historical snapshots used local naive time. Keep that uncertainty visible.
    return parsed.isoformat(timespec="seconds")


def optional_text(row: dict[str, str], name: str) -> str | None:
    value = row.get(name, "").strip()
    return value or None


def finite_number(
    row: dict[str, str], name: str, *, required: bool = False, positive: bool = False
) -> float | None:
    value = row.get(name, "").strip()
    if not value:
        if required:
            raise ValueError(f"Missing required numeric value {name}")
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"Invalid numeric value {name}={value!r}") from error
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"Invalid numeric value {name}={value!r}")
    return number


def integer_value(row: dict[str, str], name: str) -> int:
    number = finite_number(row, name, required=True, positive=True)
    assert number is not None
    if not number.is_integer():
        raise ValueError(f"{name} must be an integer, received {number}")
    return int(number)


def boolean_value(value: str, *, required: bool = False) -> int | None:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "1.0"}:
        return 1
    if normalized in {"false", "0", "0.0"}:
        return 0
    if not normalized and not required:
        return None
    raise ValueError(f"Invalid boolean value {value!r}")


def has_usable_price(row: dict[str, str], dataset: str) -> bool:
    if "has_price" in row:
        has_price = boolean_value(row.get("has_price", ""), required=True)
        if not has_price:
            return False
    ref_column = "bp_price_ref" if dataset == "unusual" else "price_ref"
    key_column = (
        "bp_price_keys_equivalent" if dataset == "unusual"
        else "price_keys_equivalent"
    )
    values = (row.get(ref_column, "").strip(), row.get(key_column, "").strip())
    if not any(values):
        return False
    return True


def read_snapshot(path: Path, dataset: str) -> tuple[list[dict[str, str]], str]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS[dataset] - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(sorted(missing))}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} contains no observations")
    timestamps = {normalized_timestamp(row["scrape_timestamp"]) for row in rows}
    if len(timestamps) != 1:
        raise ValueError(f"{path} contains multiple collection timestamps")
    return rows, timestamps.pop()


def load_quality_report(path: Path, source_hash: str) -> tuple[dict | None, str]:
    report_path = path.parent / "quality" / f"{path.stem}.quality.json"
    if not report_path.exists():
        return None, "legacy_unverified"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("processed_sha256") != source_hash:
        raise ValueError(f"Quality report hash does not match {path}")
    return report, "validated"


def row_stable_id(row: dict[str, str], dataset: str) -> str:
    stored = row.get("market_id", "").strip()
    derived = derive_market_id(row, dataset)
    if not derived:
        raise ValueError("Could not derive a stable market identity")
    if stored and stored != derived:
        raise ValueError(f"Stored market_id {stored!r} disagrees with derived identity")
    return derived


def market_values(row: dict[str, str], dataset: str, collected_at: str) -> tuple:
    stable_id = row_stable_id(row, dataset)
    if dataset == "unusual":
        defindex = integer_value(row, "defindex")
        effect_id = integer_value(row, "effect_id")
        effect_name = optional_text(row, "effect_name")
        quality = None
        craftable = 1
    else:
        defindex = None
        effect_id = None
        effect_name = None
        quality = optional_text(row, "quality")
        if quality is None:
            raise ValueError("Community market has a blank quality")
        craftable = boolean_value(row.get("craftable", ""), required=True)
    item_name = optional_text(row, "item_name")
    if item_name is None:
        raise ValueError("Market has a blank item_name")
    return (
        stable_id, dataset, defindex, effect_id, item_name, effect_name, quality,
        craftable, optional_text(row, "item_type"), optional_text(row, "slot"),
        optional_text(row, "summary"), collected_at, collected_at,
    )


def observation_values(row: dict[str, str], dataset: str) -> tuple:
    ref_column = "bp_price_ref" if dataset == "unusual" else "price_ref"
    key_column = (
        "bp_price_keys_equivalent" if dataset == "unusual"
        else "price_keys_equivalent"
    )
    source_low = finite_number(row, "source_price_low", positive=True)
    source_high = finite_number(row, "source_price_high", positive=True)
    if source_low is not None and source_high is not None and source_high < source_low:
        raise ValueError("source_price_high is below source_price_low")
    source_unit = optional_text(row, "source_price_unit")
    if source_unit not in {None, "ref", "keys"}:
        raise ValueError(f"Unsupported source_price_unit {source_unit!r}")
    raw_row = finite_number(row, "raw_row_number", positive=True)
    if raw_row is not None and (not raw_row.is_integer() or raw_row < 2):
        raise ValueError("raw_row_number must be an integer of at least 2")
    return (
        finite_number(row, ref_column, required=True, positive=True),
        finite_number(row, key_column, required=True, positive=True),
        finite_number(row, "usd_price"),
        finite_number(row, "key_price_ref", positive=True),
        source_low, source_high, source_unit,
        optional_text(row, "source_updated_at"),
        optional_text(row, "source_price_provenance"),
        optional_text(row, "key_rate_source"),
        boolean_value(row.get("price_is_range", "")),
        optional_text(row, "quality_flags"),
        int(raw_row) if raw_row is not None else None,
    )


def import_snapshot(
    connection: sqlite3.Connection, path: str | Path, dataset: str
) -> ImportResult:
    """Atomically import one snapshot; a content-identical rerun is a no-op."""

    if dataset not in REQUIRED_COLUMNS:
        raise ValueError(f"Unsupported dataset {dataset!r}")
    source_path = Path(path)
    source_hash = file_sha256(source_path)
    identical = connection.execute(
        "SELECT snapshot_id, market_count, priced_observation_count "
        "FROM snapshots WHERE dataset = ? AND source_sha256 = ?",
        (dataset, source_hash),
    ).fetchone()
    if identical:
        return ImportResult(
            source_path.name, dataset, identical["snapshot_id"],
            identical["market_count"], identical["priced_observation_count"],
            "unchanged",
        )

    rows, collected_at = read_snapshot(source_path, dataset)
    report, validation_status = load_quality_report(source_path, source_hash)
    if report is not None and report.get("accepted_rows") != len(rows):
        raise ValueError("Quality report accepted_rows does not match the CSV")

    existing = connection.execute(
        "SELECT snapshot_id, source_sha256, market_count, "
        "priced_observation_count FROM snapshots "
        "WHERE dataset = ? AND collected_at = ?",
        (dataset, collected_at),
    ).fetchone()
    if existing:
        if existing["source_sha256"] != source_hash:
            raise ValueError(
                f"A different {dataset} snapshot already exists for {collected_at}"
            )
        return ImportResult(
            source_path.name, dataset, existing["snapshot_id"],
            existing["market_count"], existing["priced_observation_count"],
            "unchanged",
        )

    prepared = []
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        try:
            identity = row_stable_id(row, dataset)
            if identity in seen:
                raise ValueError(f"Duplicate market identity {identity}")
            seen.add(identity)
            observation = (
                observation_values(row, dataset)
                if has_usable_price(row, dataset)
                else None
            )
            raw_row = finite_number(row, "raw_row_number", positive=True)
            prepared.append((
                identity,
                market_values(row, dataset, collected_at),
                observation,
                optional_text(row, "quality_flags"),
                int(raw_row) if raw_row is not None else None,
            ))
        except ValueError as error:
            raise ValueError(f"{source_path}:{row_number}: {error}") from error

    imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO snapshots (
                dataset, collected_at, source_file, source_sha256,
                cleaning_version, validation_status, imported_at,
                market_count, priced_observation_count, quality_report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset, collected_at, source_path.as_posix(), source_hash,
                report.get("cleaning_version") if report else None,
                validation_status, imported_at, len(prepared),
                sum(item[2] is not None for item in prepared),
                json.dumps(report, sort_keys=True) if report else None,
            ),
        )
        snapshot_id = cursor.lastrowid
        assert snapshot_id is not None
        connection.executemany(
                """
                INSERT INTO markets (
                    stable_id, dataset, defindex, effect_id, item_name,
                    effect_name, quality, craftable, item_type, slot, summary,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stable_id) DO UPDATE SET
                    item_name = CASE
                        WHEN excluded.last_seen_at >= markets.last_seen_at
                        THEN excluded.item_name ELSE markets.item_name END,
                    effect_name = CASE
                        WHEN excluded.last_seen_at >= markets.last_seen_at
                        THEN COALESCE(excluded.effect_name, markets.effect_name)
                        ELSE markets.effect_name END,
                    item_type = CASE
                        WHEN excluded.last_seen_at >= markets.last_seen_at
                        THEN COALESCE(excluded.item_type, markets.item_type)
                        ELSE markets.item_type END,
                    slot = CASE
                        WHEN excluded.last_seen_at >= markets.last_seen_at
                        THEN COALESCE(excluded.slot, markets.slot)
                        ELSE markets.slot END,
                    summary = CASE
                        WHEN excluded.last_seen_at >= markets.last_seen_at
                        THEN COALESCE(excluded.summary, markets.summary)
                        ELSE markets.summary END,
                    first_seen_at = MIN(markets.first_seen_at, excluded.first_seen_at),
                    last_seen_at = MAX(markets.last_seen_at, excluded.last_seen_at)
                """,
                (market for _, market, _, _, _ in prepared),
            )
        market_rows = {
            row["stable_id"]: (row["market_id"], row["dataset"])
            for row in connection.execute(
                "SELECT market_id, stable_id, dataset FROM markets"
            )
        }
        observation_rows = []
        presence_rows = []
        for identity, _, observation, quality_flags, raw_row_number in prepared:
            market_key, market_dataset = market_rows[identity]
            if market_dataset != dataset:
                raise ValueError(f"Market identity {identity} changed dataset")
            presence_rows.append((
                snapshot_id, market_key,
                "priced" if observation is not None else "unpriced",
                quality_flags, raw_row_number,
            ))
            if observation is not None:
                observation_rows.append((snapshot_id, market_key, *observation))
        connection.executemany(
            "INSERT INTO market_presence VALUES (?, ?, ?, ?, ?)",
            presence_rows,
        )
        connection.executemany(
                """
                INSERT INTO price_observations (
                    snapshot_id, market_id, price_ref, price_keys, price_usd,
                    key_price_ref, source_price_low, source_price_high,
                    source_price_unit, source_updated_at,
                    source_price_provenance, key_rate_source, price_is_range,
                    quality_flags, raw_row_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                observation_rows,
            )
        if report:
            for issue_kind, field in (
                ("warning", "warning_counts"), ("rejection", "rejection_counts")
            ):
                for code, count in report.get(field, {}).items():
                    connection.execute(
                        "INSERT INTO snapshot_quality_issues VALUES (?, ?, ?, ?)",
                        (snapshot_id, code, issue_kind, int(count)),
                    )
        actual = connection.execute(
            "SELECT COUNT(*) FROM price_observations WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()[0]
        expected_priced = sum(item[2] is not None for item in prepared)
        if actual != expected_priced:
            raise RuntimeError(
                f"Observation verification failed: expected {expected_priced}, got {actual}"
            )
    return ImportResult(
        source_path.name, dataset, snapshot_id, len(prepared), expected_priced,
        "imported",
    )


def discover_snapshots(processed_root: str | Path) -> list[tuple[Path, str]]:
    root = Path(processed_root)
    unusual = sorted(path for path in root.glob("cleaned_*.csv") if path.is_file())
    community = sorted(
        path for path in (root / "non_unusual").glob("community_prices_*.csv")
        if path.is_file()
    )
    return [*((path, "unusual") for path in unusual),
            *((path, "community") for path in community)]


def import_directory(
    connection: sqlite3.Connection, processed_root: str | Path
) -> list[ImportResult]:
    return [
        import_snapshot(connection, path, dataset)
        for path, dataset in discover_snapshots(processed_root)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="*")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--dataset", choices=sorted(REQUIRED_COLUMNS),
        help="Required when importing explicit CSV paths.",
    )
    parser.add_argument(
        "--processed-root", type=Path,
        help="Discover both dataset types below this processed-data directory.",
    )
    args = parser.parse_args()
    if bool(args.paths) == bool(args.processed_root):
        parser.error("provide explicit paths or --processed-root, but not both")
    if args.paths and not args.dataset:
        parser.error("--dataset is required for explicit paths")
    with connect_database(args.database) as connection:
        results = (
            import_directory(connection, args.processed_root)
            if args.processed_root
            else [import_snapshot(connection, path, args.dataset) for path in args.paths]
        )
    imported = sum(result.action == "imported" for result in results)
    markets = sum(result.markets for result in results)
    observations = sum(result.priced_observations for result in results)
    print(
        f"Processed {len(results):,} snapshots: {imported:,} imported, "
        f"{len(results) - imported:,} unchanged; "
        f"{markets:,} markets and {observations:,} priced observations verified."
    )


if __name__ == "__main__":
    main()
