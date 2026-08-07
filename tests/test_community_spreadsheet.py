import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scraper.community_spreadsheet import parse_community_spreadsheet, run_scraper


SAMPLE_HTML = """
<table id="pricelist">
  <thead>
    <tr><th>Name</th><th>Type</th><th>Unique</th><th>Strange</th></tr>
  </thead>
  <tbody>
    <tr data-craftable="1">
      <td>Team Captain</td><td>Cosmetic</td>
      <td abbr="50.5"><a href="/stats/Unique/Team%20Captain" title="$1.54">50-51 ref</a></td>
      <td abbr="0"></td>
    </tr>
  </tbody>
</table>
"""


class CommunitySpreadsheetParserTests(unittest.TestCase):
    def test_parses_non_zero_quality_cells(self):
        rows = parse_community_spreadsheet(
            SAMPLE_HTML,
            scraped_at=datetime(2026, 8, 7, 12, 0, 0),
        )

        self.assertEqual(len(rows), 1)
        row = rows.iloc[0]
        self.assertEqual(row["item_name"], "Team Captain")
        self.assertEqual(row["quality"], "Unique")
        self.assertEqual(row["price_ref"], 50.5)
        self.assertTrue(row["craftable"])
        self.assertEqual(row["usd_price"], 1.54)
        self.assertEqual(
            row["stats_url"],
            "https://backpack.tf/stats/Unique/Team%20Captain",
        )

    @patch("scraper.community_spreadsheet.fetch_community_snapshot")
    def test_scrape_also_creates_a_cleaned_snapshot(self, fetch_spreadsheet):
        fetch_spreadsheet.return_value = (SAMPLE_HTML, 50.0)

        with TemporaryDirectory() as temporary_directory:
            raw_directory = Path(temporary_directory) / "raw"
            result = run_scraper(
                output_dir=raw_directory,
                scraped_at=datetime(2026, 8, 7, 12, 0, 0),
            )

            self.assertTrue(result.raw_csv.exists())
            self.assertTrue(result.processed_csv.exists())
            self.assertEqual(result.row_count, 1)
            self.assertIn("processed", result.processed_csv.parts)


if __name__ == "__main__":
    unittest.main()
