import unittest

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


if __name__ == "__main__":
    unittest.main()
