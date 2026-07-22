import csv
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from scraper.main import main
from scraper.scraper import build_output_paths, run_scraper


SAMPLE_HAT = {
    "effect_id": "99",
    "effect_name": "Arcana",
    "item_name": "Test Hat",
    "bp_price_ref": "100",
    "bp_price_keys": "2 keys",
    "bp_price_all": "100 ref, $3.00",
    "exist": "1",
    "slot": "misc",
    "summary": "Level 1-100",
    "defindex": "123",
    "scrape_timestamp": "2026-07-22T12:00:00",
}


class ScraperPipelineTests(unittest.TestCase):
    @patch("scraper.main.import_module")
    @patch("scraper.main.cloudflare_challenge_is_active", return_value=False)
    @patch("scraper.main.launch_chrome")
    def test_main_launches_chrome_then_calls_scraper_pipeline(
        self,
        launch_chrome,
        _cloudflare_challenge_is_active,
        import_module_mock,
    ):
        scraper_module = MagicMock()
        import_module_mock.return_value = scraper_module

        main()

        launch_chrome.assert_called_once_with()
        import_module_mock.assert_called_once_with("scraper.scraper")
        scraper_module.run_scraper.assert_called_once_with()

    def test_build_output_paths_uses_output_dir_environment_variable(self):
        with patch.dict(os.environ, {"OUTPUT_DIR": "temporary-output"}):
            raw_csv, processed_csv = build_output_paths(
                scrape_datetime=datetime(2026, 7, 22, 12, 0, 0)
            )

        self.assertEqual(
            raw_csv,
            Path("temporary-output/raw/unusuals_2026-07-22_12-00-00.csv"),
        )
        self.assertEqual(
            processed_csv,
            Path("temporary-output/processed/cleaned_2026-07-22_12-00-00.csv"),
        )

    @patch("scraper.scraper.clean_data")
    @patch("scraper.scraper.get_all_effects")
    @patch("scraper.scraper.get_key_market")
    @patch("scraper.scraper.get_driver")
    def test_run_scraper_checkpoints_rows_cleans_and_returns_paths(
        self,
        get_driver,
        get_key_market,
        get_all_effects,
        clean_data_mock,
    ):
        driver = MagicMock()
        get_driver.return_value = driver
        get_key_market.return_value = {"mid_price": 60.0}
        get_all_effects.return_value = [{"effect_name": "Arcana"}]

        with tempfile.TemporaryDirectory() as output_dir:
            with patch("scraper.scraper.scrape_effect", return_value=[SAMPLE_HAT]):
                result = run_scraper(
                    output_dir=output_dir,
                    request_delay_seconds=0,
                    scrape_datetime=datetime(2026, 7, 22, 12, 0, 0),
                )

            self.assertTrue(result.raw_csv.is_file())
            with result.raw_csv.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))

            self.assertEqual(rows, [SAMPLE_HAT])
            self.assertEqual(result.row_count, 1)
            clean_data_mock.assert_called_once_with(
                result.raw_csv,
                result.processed_csv,
                60.0,
            )

        driver.quit.assert_called_once_with()

    @patch("scraper.scraper.get_all_effects", side_effect=RuntimeError("page failed"))
    @patch("scraper.scraper.get_key_market", return_value={"mid_price": 60.0})
    @patch("scraper.scraper.get_driver")
    def test_run_scraper_always_closes_driver(
        self,
        get_driver,
        _get_key_market,
        _get_all_effects,
    ):
        driver = MagicMock()
        get_driver.return_value = driver

        with tempfile.TemporaryDirectory() as output_dir:
            with self.assertRaisesRegex(RuntimeError, "page failed"):
                run_scraper(output_dir=output_dir, request_delay_seconds=0)

        driver.quit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
