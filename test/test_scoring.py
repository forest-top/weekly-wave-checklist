import unittest

from scripts.scoring import SOFT_KEYS, score_candidate


def candidate(**overrides):
    values = {key: True for key in SOFT_KEYS}
    values.update({"main_board": True, "data_complete": True, "market_gate": True})
    values.update(overrides)
    return values


class ScoringTests(unittest.TestCase):
    def test_perfect_candidate_gets_five_stars(self):
        result = score_candidate(candidate())
        self.assertEqual(result["stars"], 5)
        self.assertEqual(result["soft_misses"], 0)
        self.assertEqual(result["action"], "允许进入人工执行")

    def test_three_soft_misses_is_four_star_small_position_candidate(self):
        misses = dict.fromkeys(SOFT_KEYS[:3], False)
        result = score_candidate(candidate(**misses))
        self.assertEqual(result["stars"], 4)
        self.assertEqual(result["soft_misses"], 3)
        self.assertEqual(result["action"], "等待补齐后小仓")

    def test_four_soft_misses_is_three_star_observation(self):
        misses = dict.fromkeys(SOFT_KEYS[:4], False)
        result = score_candidate(candidate(**misses))
        self.assertEqual(result["stars"], 3)
        self.assertEqual(result["soft_misses"], 4)
        self.assertEqual(result["action"], "仅观察/模拟")

    def test_market_gate_is_advisory_for_five_star_technical_setup(self):
        result = score_candidate(candidate(market_gate=False))
        self.assertEqual(result["stars"], 5)
        self.assertEqual(result["action"], "允许进入人工执行")


if __name__ == "__main__":
    unittest.main()
