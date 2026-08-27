import unittest
from unittest.mock import patch

from scripts import screen
from scripts.screen import select_scope


class ScreenScopeTests(unittest.TestCase):
    def test_zero_limit_keeps_every_main_board_quote(self):
        rows = [
            {"f12": "000001"}, {"f12": "600000"}, {"f12": "300750"}, {"f12": "688981"},
        ]
        selected = select_scope(rows, 0)
        self.assertEqual([row["f12"] for row in selected], ["000001", "600000"])

    def test_positive_limit_is_only_an_explicit_test_cap(self):
        rows = [{"f12": "000001"}, {"f12": "600000"}, {"f12": "601000"}]
        self.assertEqual(len(select_scope(rows, 2)), 2)

    @patch("scripts.screen.fetch_json")
    def test_keeps_todays_available_kline_for_intraday_scan(self, fetch_json):
        fetch_json.return_value = {
            "data": {"sz000001": {"qfqday": [
                ["2026-08-26", "1", "1", "1", "1", "1"],
                [screen.TODAY_CN, "1", "1", "1", "1", "1"],
                ["2099-01-01", "1", "1", "1", "1", "1"],
            ]}}
        }
        rows = screen.fetch_kline("000001")
        self.assertEqual([row[0] for row in rows], ["2026-08-26", screen.TODAY_CN])

    def test_rejects_an_incomplete_main_board_universe(self):
        with self.assertRaises(RuntimeError):
            screen.validate_main_board_scope([{"f12": "000001"}] * 57)

    @patch("scripts.screen.fetch_json")
    def test_retries_a_quote_page_on_an_alternate_official_host(self, fetch_json):
        fetch_json.side_effect = [OSError("502"), {"data": {"diff": [{"f12": "000001"}]}}]
        payload = screen.fetch_quote_page("https://push2.eastmoney.com/api/qt/clist/get?pn=1")
        self.assertEqual(payload["data"]["diff"][0]["f12"], "000001")
        self.assertEqual(fetch_json.call_count, 2)
        self.assertIn("82.push2.eastmoney.com", fetch_json.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
