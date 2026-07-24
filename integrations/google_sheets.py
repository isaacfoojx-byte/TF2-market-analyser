from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from scripts.validate_scrape_output import REQUIRED_PROCESSED_COLUMNS


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TRANSIENT_HTTP_STATUSES = {429, 500, 502, 503, 504}
DEFAULT_BATCH_ROWS = 2000
DEFAULT_MAX_ATTEMPTS = 5
INTEGER_PATTERN = re.compile(r"^-?\d+$")
FLOAT_PATTERN = re.compile(r"^-?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?$")


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


def load_processed_csv(csv_path: Path) -> tuple[list[str], list[list[Any]], str]:
    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        missing = REQUIRED_PROCESSED_COLUMNS - set(headers)
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
    properties = next(
        (
            sheet.get("properties", {})
            for sheet in response.get("sheets", [])
            if sheet.get("properties", {}).get("title") == sheet_name
        ),
        None,
    )
    if properties is None:
        raise ValueError(f"Spreadsheet does not contain a tab named {sheet_name!r}")

    grid = properties.get("gridProperties", {})
    current_rows = int(grid.get("rowCount", 0))
    current_columns = int(grid.get("columnCount", 0))
    target_rows = max(current_rows, required_rows)
    target_columns = max(current_columns, required_columns)

    if target_rows == current_rows and target_columns == current_columns:
        return

    resize_request = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": properties["sheetId"],
                            "gridProperties": {
                                "rowCount": target_rows,
                                "columnCount": target_columns,
                            },
                        },
                        "fields": (
                            "gridProperties(rowCount,columnCount)"
                        ),
                    }
                }
            ]
        },
    )
    execute_with_retry(resize_request)
    print(
        f"Expanded {sheet_name!r} grid to "
        f"{target_rows:,} rows and {target_columns:,} columns"
    )


def upload_csv_to_latest(
    csv_path: str | Path,
    service=None,
    spreadsheet_id: str | None = None,
    sheet_name: str | None = None,
    batch_rows: int | None = None,
    max_rows: int | None = None,
) -> UploadResult:
    path = Path(csv_path)
    headers, rows, scrape_timestamp = load_processed_csv(path)

    if max_rows is not None:
        if max_rows < 1:
            raise ValueError("Maximum row count must be positive")
        rows = rows[:max_rows]

    target_spreadsheet = spreadsheet_id or required_environment(
        "GOOGLE_SPREADSHEET_ID"
    )
    target_sheet = sheet_name or os.environ.get("GOOGLE_SHEET_NAME", "Latest")
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--sheet-name")
    parser.add_argument("--batch-rows", type=int)
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    result = upload_csv_to_latest(
        args.csv_path,
        sheet_name=args.sheet_name,
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
