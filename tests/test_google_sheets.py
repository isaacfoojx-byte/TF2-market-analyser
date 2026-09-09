import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from integrations.google_sheets import (
    HISTORY_HEADERS, daily_summary, ensure_sheet_capacity,
    upload_csv_to_latest, upload_daily_summary,
)
from scripts.validate_scrape_output import REQUIRED_PROCESSED_COLUMNS


def service_with_sheets(sheets):
    service = MagicMock()
    service.spreadsheets().get().execute.return_value = {"sheets": sheets}
    return service


def sheet(name, rows, columns, sheet_id=1):
    return {"properties": {"title": name, "sheetId": sheet_id,
            "gridProperties": {"rowCount": rows, "columnCount": columns}}}


class GoogleSheetsTests(unittest.TestCase):
    def test_full_workbook_fails_without_mutating_archive(self):
        service = service_with_sheets([sheet("2026-08-18", 625000, 16)])
        with self.assertRaisesRegex(RuntimeError, "fresh spreadsheet"):
            ensure_sheet_capacity(service, "book", "Latest", 41512, 16)
        service.spreadsheets().batchUpdate.assert_not_called()

    def test_existing_latest_reuses_capacity_at_limit(self):
        service = service_with_sheets([sheet("Latest", 625000, 16)])
        ensure_sheet_capacity(service, "book", "Latest", 41512, 16)
        service.spreadsheets().batchUpdate.assert_not_called()

    def test_new_tab_uses_exact_capacity_without_trimming_archives(self):
        service = service_with_sheets([sheet("2026-08-18", 40000, 26)])
        ensure_sheet_capacity(service, "book", "Latest", 41512, 16)
        operations = service.spreadsheets().batchUpdate.call_args.kwargs["body"]["requests"]
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["addSheet"]["properties"]["gridProperties"],
                         {"rowCount": 41512, "columnCount": 16})

    def history_service(self, existing, summary):
        service = service_with_sheets([sheet("Daily History", 100, 8)])
        service.spreadsheets().values().get().execute.side_effect = [
            {"values": existing}, {"values": [summary]},
        ]
        return service

    def test_history_rerun_updates_same_row(self):
        old = ["2026-09-09", "2026-09-09T01:00:00", "unusual", 2, 2, 3, 3, "old.csv"]
        new = ["2026-09-09", "2026-09-09T02:00:00", "unusual", 3, 3, 4, 4, "new.csv"]
        service = self.history_service([HISTORY_HEADERS, old], new)
        upload_daily_summary(service, "book", new)
        data = service.spreadsheets().values().batchUpdate.call_args.kwargs["body"]["data"]
        self.assertEqual(data[1]["range"], "'Daily History'!A2:H2")
        self.assertEqual(data[1]["values"], [new])

    def test_next_day_preserves_previous_rows(self):
        old = ["2026-09-08", "2026-09-08T01:00:00", "unusual", 2, 2, 3, 3, "old.csv"]
        new = ["2026-09-09", "2026-09-09T02:00:00", "unusual", 3, 3, 4, 4, "new.csv"]
        service = self.history_service([HISTORY_HEADERS, old], new)
        upload_daily_summary(service, "book", new)
        data = service.spreadsheets().values().batchUpdate.call_args.kwargs["body"]["data"]
        self.assertEqual(data[1]["range"], "'Daily History'!A3:H3")
        service.spreadsheets().values().clear.assert_not_called()

    def test_history_rejects_unknown_headers(self):
        summary = ["2026-09-09", "2026-09-09T01:00:00", "unusual", 2, 2, 3, 3, "x.csv"]
        service = self.history_service([["personal notes"]], summary)
        with self.assertRaisesRegex(ValueError, "unexpected headers"):
            upload_daily_summary(service, "book", summary)
        service.spreadsheets().values().batchUpdate.assert_not_called()

    def test_older_same_day_summary_cannot_overwrite_newer(self):
        old = ["2026-09-09", "2026-09-09T01:00:00", "unusual", 2, 2, 3, 3, "old.csv"]
        new = ["2026-09-09", "2026-09-09T02:00:00", "unusual", 3, 3, 4, 4, "new.csv"]
        service = self.history_service([HISTORY_HEADERS, new], old)
        with self.assertRaisesRegex(ValueError, "newer daily summary"):
            upload_daily_summary(service, "book", old)
        service.spreadsheets().values().batchUpdate.assert_not_called()

    def test_readback_accepts_sheets_numeric_precision(self):
        summary = ["2026-09-09", "2026-09-09T01:00:00", "unusual", 3, 3,
                   1.2345678901234567, 1.0, "x.csv"]
        rounded = [*summary]
        rounded[5] = 1.23456789012346
        service = self.history_service([], rounded)
        upload_daily_summary(service, "book", summary)

    def test_readback_rejects_incorrect_values(self):
        summary = ["2026-09-09", "2026-09-09T01:00:00", "unusual", 3, 3, 2, 2, "x.csv"]
        service = self.history_service([], [*summary[:5], 99, 2, "x.csv"])
        with self.assertRaisesRegex(RuntimeError, "read-back"):
            upload_daily_summary(service, "book", summary)

    def test_community_summary_uses_community_price_column(self):
        from processing.community_prices import COLUMN_ORDER
        with TemporaryDirectory() as directory:
            path = Path(directory) / "community.csv"
            with path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=COLUMN_ORDER)
                writer.writeheader()
                writer.writerow({"scrape_timestamp": "2026-09-09T01:00:00",
                                 "price_keys_equivalent": 2.5})
            summary = daily_summary(path, "community")
            self.assertEqual(summary[2:7], ["community", 1, 1, 2.5, 2.5])

    def write_csv(self, path):
        headers = sorted(REQUIRED_PROCESSED_COLUMNS)
        rows = []
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            for price in [2, 4, 0]:
                row = {header: "" for header in headers}
                row.update(scrape_timestamp="2026-09-09T01:00:00",
                           bp_price_keys_equivalent=price)
                writer.writerow(row)
                rows.append([row[h] for h in headers])
        return headers, rows

    def test_summary_counts_markets_and_excludes_nonpositive_prices(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.csv"
            self.write_csv(path)
            self.assertEqual(daily_summary(path, "unusual"),
                             ["2026-09-09", "2026-09-09T01:00:00", "unusual", 3, 2, 3, 3, "snapshot.csv"])

    def test_default_upload_replaces_latest_and_clears_stale_rows(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.csv"
            headers, rows = self.write_csv(path)
            service = service_with_sheets([sheet("Latest", 100, len(headers))])
            service.spreadsheets().values().get().execute.return_value = {"values": [headers, *rows]}
            service.spreadsheets().values().batchUpdate().execute.return_value = {"totalUpdatedCells": 40}
            result = upload_csv_to_latest(path, service=service, spreadsheet_id="book")
            self.assertEqual(result.sheet_name, "Latest")
            self.assertEqual(result.verified_rows, 3)
            service.spreadsheets().values().clear.assert_called_once_with(
                spreadsheetId="book", range="'Latest'", body={},
            )


if __name__ == "__main__":
    unittest.main()
