from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from processing.community_prices import COLUMN_ORDER as COMMUNITY_PROCESSED_COLUMNS
from scripts.validate_scrape_output import REQUIRED_PROCESSED_COLUMNS


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TRANSIENT_HTTP_STATUSES = {429, 500, 502, 503, 504}
DEFAULT_BATCH_ROWS = 2000
DEFAULT_MAX_ATTEMPTS = 5
INTEGER_PATTERN = re.compile(r"^-?\d+$")
FLOAT_PATTERN = re.compile(r"^-?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?$")
SCHEMA_REQUIRED_COLUMNS = {
    "unusual": REQUIRED_PROCESSED_COLUMNS,
    "community": set(COMMUNITY_PROCESSED_COLUMNS),
}


@dataclass(frozen=True)
class UploadResult:
    spreadsheet_id: str
    sheet_name: str
    row_count: int
    column_count: int
    scrape_timestamp: str
    updated_cells: int
    verified_rows: int


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_service_from_environment():
    credentials_info = json.loads(required_environment("GOOGLE_SERVICE_ACCOUNT_JSON"))
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=[SHEETS_SCOPE],
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def coerce_value(value: str) -> Any:
    stripped = value.strip()
    lowered = stripped.lower()

    if stripped == "":
        return ""
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if INTEGER_PATTERN.fullmatch(stripped):
        return int(stripped)
    if FLOAT_PATTERN.fullmatch(stripped):
        number = float(stripped)
        if math.isfinite(number):
            return number

    return value


def load_processed_csv(
    csv_path: Path,
    required_columns: set[str] | None = None,
) -> tuple[list[str], list[list[Any]], str]:
    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        expected_columns = required_columns or REQUIRED_PROCESSED_COLUMNS
        missing = expected_columns - set(headers)
        if missing:
            raise ValueError(
                f"{csv_path} is missing required columns: {', '.join(sorted(missing))}"
            )

        rows = [[coerce_value(row.get(header, "")) for header in headers] for row in reader]

    if not rows:
        raise ValueError(f"{csv_path} contains no data rows")

    timestamp_index = headers.index("scrape_timestamp")
    scrape_timestamp = str(rows[0][timestamp_index])
    return headers, rows, scrape_timestamp


def execute_with_retry(
    request,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
    random_value: Callable[[], float] = random.random,
):
    for attempt in range(max_attempts):
        try:
            return request.execute()
        except HttpError as error:
            status = getattr(error.resp, "status", None)
            if status not in TRANSIENT_HTTP_STATUSES or attempt == max_attempts - 1:
                raise
            sleep(min(2**attempt + random_value(), 32))

    raise RuntimeError("Google Sheets request exhausted its retry attempts")


def quote_sheet_name(sheet_name: str) -> str:
    return "'" + sheet_name.replace("'", "''") + "'"


def column_name(column_number: int) -> str:
    if column_number < 1:
        raise ValueError("Column number must be positive")

    result = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def sheet_name_from_timestamp(scrape_timestamp: str) -> str:
    normalized = scrape_timestamp.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError as error:
        raise ValueError(
            f"Invalid scrape_timestamp for sheet naming: {scrape_timestamp!r}"
        ) from error


def ensure_sheet_capacity(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    required_rows: int,
    required_columns: int,
) -> None:
    request = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields=(
            "sheets.properties("
            "sheetId,title,gridProperties(rowCount,columnCount)"
            ")"
        ),
    )
    response = execute_with_retry(request)
    sheets = response.get("sheets", [])
    properties = next(
        (
            sheet.get("properties", {})
            for sheet in sheets
            if sheet.get("properties", {}).get("title") == sheet_name
        ),
        None,
    )
    grid = (properties or {}).get("gridProperties", {})
    current_rows = int(grid.get("rowCount", 0))
    current_columns = int(grid.get("columnCount", 0))
    target_rows = max(current_rows, required_rows)
    target_columns = max(current_columns, required_columns)
    allocated_cells = sum(
        int(sheet.get("properties", {}).get("gridProperties", {}).get("rowCount", 0))
        * int(sheet.get("properties", {}).get("gridProperties", {}).get("columnCount", 0))
        for sheet in sheets
    )
    projected_cells = (
        allocated_cells - current_rows * current_columns
        + target_rows * target_columns
    )
    if projected_cells > 10_000_000:
        raise RuntimeError(
            f"Cannot publish {sheet_name!r}: workbook would need "
            f"{projected_cells:,} cells (limit 10,000,000). "
            "Keep this workbook as an archive and configure a fresh spreadsheet "
            "shared with the service account. This capacity check did not modify any tabs."
        )

    if properties is None:
        operation = {
            "addSheet": {
                "properties": {
                    "title": sheet_name,
                    "gridProperties": {
                        "rowCount": target_rows,
                        "columnCount": target_columns,
                    },
                }
            }
        }
    elif target_rows == current_rows and target_columns == current_columns:
        return
    else:
        operation = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": properties["sheetId"],
                    "gridProperties": {
                        "rowCount": target_rows,
                        "columnCount": target_columns,
                    },
                },
                "fields": "gridProperties(rowCount,columnCount)",
            }
        }
    execute_with_retry(service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": [operation]},
    ))


def upload_csv_to_latest(
    csv_path: str | Path,
    service=None,
    spreadsheet_id: str | None = None,
    spreadsheet_id_env: str = "GOOGLE_SPREADSHEET_ID",
    schema: str = "unusual",
    sheet_name: str | None = None,
    batch_rows: int | None = None,
    max_rows: int | None = None,
) -> UploadResult:
    path = Path(csv_path)
    required_columns = SCHEMA_REQUIRED_COLUMNS.get(schema)
    if required_columns is None:
        supported = ", ".join(sorted(SCHEMA_REQUIRED_COLUMNS))
        raise ValueError(f"Unsupported CSV schema {schema!r}. Choose one of: {supported}")

    headers, rows, scrape_timestamp = load_processed_csv(path, required_columns)

    if max_rows is not None:
        if max_rows < 1:
            raise ValueError("Maximum row count must be positive")
        rows = rows[:max_rows]

    target_spreadsheet = spreadsheet_id or required_environment(spreadsheet_id_env)
    target_sheet = (
        sheet_name
        or os.environ.get("GOOGLE_SHEET_NAME")
        or "Latest"
    )
    if target_sheet == "Daily History":
        raise ValueError("Daily History is reserved for summary rows")
    sheet_name_from_timestamp(scrape_timestamp)
    rows_per_batch = (
        batch_rows
        if batch_rows is not None
        else int(os.environ.get("GOOGLE_SHEETS_BATCH_ROWS", DEFAULT_BATCH_ROWS))
    )

    if rows_per_batch < 1:
        raise ValueError("Batch row count must be positive")

    values = [headers, *rows]
    sheets_service = service or build_service_from_environment()
    ensure_sheet_capacity(
        sheets_service,
        target_spreadsheet,
        target_sheet,
        required_rows=len(values),
        required_columns=len(headers),
    )
    quoted_sheet = quote_sheet_name(target_sheet)

    clear_request = sheets_service.spreadsheets().values().clear(
        spreadsheetId=target_spreadsheet,
        range=quoted_sheet,
        body={},
    )
    execute_with_retry(clear_request)

    last_column = column_name(len(headers))
    updated_cells = 0

    for start_index in range(0, len(values), rows_per_batch):
        batch = values[start_index : start_index + rows_per_batch]
        start_row = start_index + 1
        end_row = start_row + len(batch) - 1
        target_range = f"{quoted_sheet}!A{start_row}:{last_column}{end_row}"
        request = sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=target_spreadsheet,
            body={
                "valueInputOption": "RAW",
                "data": [{"range": target_range, "values": batch}],
            },
        )
        response = execute_with_retry(request)
        updated_cells += int(response.get("totalUpdatedCells", 0))

    written_range = f"{quoted_sheet}!A1:{last_column}{len(values)}"
    verify_request = sheets_service.spreadsheets().values().get(
        spreadsheetId=target_spreadsheet,
        range=written_range,
        majorDimension="ROWS",
    )
    verified_values = execute_with_retry(verify_request).get("values", [])
    if not verified_values or verified_values[0] != headers:
        raise RuntimeError("Google Sheets read-back header verification failed")

    verified_rows = len(verified_values) - 1
    if verified_rows != len(rows):
        raise RuntimeError(
            f"Google Sheets read-back row mismatch: expected={len(rows)}, "
            f"actual={verified_rows}"
        )

    return UploadResult(
        spreadsheet_id=target_spreadsheet,
        sheet_name=target_sheet,
        row_count=len(rows),
        column_count=len(headers),
        scrape_timestamp=scrape_timestamp,
        updated_cells=updated_cells,
        verified_rows=verified_rows,
    )


HISTORY_HEADERS = [
    "date", "scrape_timestamp", "schema", "market_count", "priced_market_count",
    "mean_price_keys", "median_price_keys", "source_csv",
]


def daily_summary(csv_path: Path, schema: str) -> list[Any]:
    headers, rows, timestamp = load_processed_csv(
        csv_path, SCHEMA_REQUIRED_COLUMNS[schema],
    )
    timestamps = {str(row[headers.index("scrape_timestamp")]) for row in rows}
    if len(timestamps) != 1:
        raise ValueError("Daily summary requires exactly one scrape timestamp")
    price_column = (
        "bp_price_keys_equivalent" if schema == "unusual"
        else "price_keys_equivalent"
    )
    index = headers.index(price_column)
    prices = []
    for row in rows:
        try:
            price = float(row[index])
        except (TypeError, ValueError):
            continue
        if math.isfinite(price) and price > 0:
            prices.append(price)
    return [
        sheet_name_from_timestamp(timestamp), timestamp, schema, len(rows),
        len(prices), statistics.mean(prices) if prices else "",
        statistics.median(prices) if prices else "", csv_path.name,
    ]


def upload_daily_summary(service, spreadsheet_id: str, summary: list[Any]) -> None:
    """Upsert by date/schema; deterministic ranges make retries idempotent.

    Callers must serialize writers to each workbook (the daily workflows do).
    """
    name = "Daily History"
    ensure_sheet_capacity(service, spreadsheet_id, name, 2, len(HISTORY_HEADERS))
    quoted = quote_sheet_name(name)
    end_column = column_name(len(HISTORY_HEADERS))
    existing = execute_with_retry(service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{quoted}!A:{end_column}",
    )).get("values", [])
    if existing and existing[0] != HISTORY_HEADERS:
        raise ValueError("Daily History has unexpected headers; existing data was preserved")
    matching = [
        (index, row) for index, row in enumerate(existing[1:], start=2)
        if len(row) >= 3 and row[0] == summary[0] and row[2] == summary[2]
    ]
    if len(matching) > 1:
        raise ValueError("Daily History has duplicate date/schema rows; reconcile them first")
    target_row = matching[0][0] if matching else max(2, len(existing) + 1)
    if matching:
        def utc_timestamp(value):
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed

        previous_timestamp = utc_timestamp(matching[0][1][1])
        incoming_timestamp = utc_timestamp(summary[1])
        if incoming_timestamp < previous_timestamp:
            raise ValueError("Refusing to replace a newer daily summary with an older snapshot")
    ensure_sheet_capacity(service, spreadsheet_id, name, target_row, len(HISTORY_HEADERS))
    target_range = f"{quoted}!A{target_row}:{end_column}{target_row}"
    execute_with_retry(service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "RAW", "data": [
            {"range": f"{quoted}!A1:{end_column}1", "values": [HISTORY_HEADERS]},
            {"range": target_range, "values": [summary]},
        ]},
    ))
    actual = execute_with_retry(service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=target_range,
        valueRenderOption="UNFORMATTED_VALUE",
    )).get("values", [])
    def equal_value(expected, received):
        if isinstance(expected, float) and isinstance(received, (int, float)):
            # Sheets stores fewer significant digits than a Python float.
            return math.isclose(expected, received, rel_tol=1e-12, abs_tol=1e-12)
        return expected == received

    if (not actual or len(actual[0]) != len(summary)
            or not all(equal_value(a, b) for a, b in zip(summary, actual[0]))):
        raise RuntimeError("Daily History read-back verification failed")
    print(f"Verified daily summary for {summary[0]} ({summary[2]})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--sheet-name")
    parser.add_argument(
        "--schema",
        choices=sorted(SCHEMA_REQUIRED_COLUMNS),
        default="unusual",
        help="CSV schema to validate before upload.",
    )
    parser.add_argument(
        "--spreadsheet-id-env",
        default="GOOGLE_SPREADSHEET_ID",
        help="Environment variable containing the target spreadsheet ID.",
    )
    parser.add_argument("--batch-rows", type=int)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument(
        "--daily-history", action="store_true",
        help="Also upsert a compact daily summary in the Daily History tab.",
    )
    args = parser.parse_args()
    if args.daily_history and (args.max_rows is not None or args.sheet_name):
        parser.error("--daily-history cannot be combined with sample or custom-tab uploads")
    service = build_service_from_environment()
    summary = daily_summary(args.csv_path, args.schema) if args.daily_history else None
    if summary is not None:
        # Write history first so a retry can recover either stage safely.
        upload_daily_summary(
            service, required_environment(args.spreadsheet_id_env), summary,
        )

    result = upload_csv_to_latest(
        args.csv_path,
        service=service,
        spreadsheet_id_env=args.spreadsheet_id_env,
        schema=args.schema,
        sheet_name="Latest" if args.daily_history else args.sheet_name,
        batch_rows=args.batch_rows,
        max_rows=args.max_rows,
    )
    print(
        f"Uploaded and verified {result.verified_rows:,} rows and "
        f"{result.updated_cells:,} cells "
        f"to {result.sheet_name!r} for snapshot {result.scrape_timestamp}"
    )


if __name__ == "__main__":
    main()
