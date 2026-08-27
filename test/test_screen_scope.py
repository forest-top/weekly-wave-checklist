import unittest
import datetime as dt
from unittest.mock import patch

from scripts import screen
from scripts.screen import select_scope


class ScreenScopeTests(unittest.TestCase):

    @patch("scripts.screen.fetch_kline")
    def test_evaluate_accepts_string_prices_from_kline_source(self, fetch_kline):
        start = dt.date(2025, 1, 1)
        rows = []
        for offset in range(500):
            date = start + dt.timedelta(days=offset)
            if date.weekday() < 5:
                price = 10 + len(rows) * 0.01
                rows.append([date.isoformat(), str(price - 0.1), str(price), str(price + 0.1), str(price - 0.2), "1000"])
        fetch_kline.return_value = rows
        result = screen.evaluate(
            {"f12": "000001", "f14": "平安银行", "f23": 1, "f6": 0, "f20": 0},
            {"five_day_return": 0, "gate": False},
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["total"], 12)
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
        self.assertIn("param=sz000001%2Cday%2C%2C%2C360%2Cqfq", fetch_json.call_args.args[0])

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

    @patch("scripts.screen.fetch_cninfo_quotes")
    @patch("scripts.screen.fetch_quote_page", side_effect=OSError("source unavailable"))
    def test_falls_back_to_cninfo_when_quote_pages_are_unavailable(self, _, fetch_cninfo_quotes):
        fetch_cninfo_quotes.return_value = [{"f12": "000001", "f14": "平安银行"}] * 2500
        stocks = screen.fetch_quotes(1)
        self.assertEqual(len(stocks), 2500)
        fetch_cninfo_quotes.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
