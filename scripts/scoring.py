SOFT_KEYS = (
    "board_proxy",
    "daily_trend",
    "weekly_trend",
    "weekly_macd",
    "wave_structure",
    "wave_retracement",
    "valuation",
    "entry_bias",
    "ma_gap",
    "pullback",
    "volume",
    "not_extended",
)


def score_candidate(metrics):
    passed = sum(bool(metrics.get(key)) for key in SOFT_KEYS)
    total = len(SOFT_KEYS)
    ratio = passed / total
    misses = total - passed
    if ratio == 1:
        stars = 5
    elif ratio >= 0.75:
        stars = 4
    elif ratio >= 2 / 3:
        stars = 3
    elif ratio >= 0.7:
        stars = 2
    else:
        stars = 1

    if not metrics.get("main_board", False):
        action = "放弃：非沪深主板"
    elif not metrics.get("data_complete", False):
        action = "放弃：数据不完整"
    elif ratio >= 1:
        action = "允许进入人工执行"
    elif ratio >= 0.75:
        action = "等待补齐后小仓"
    elif ratio >= 2 / 3:
        action = "仅观察/模拟"
    else:
        action = "放弃"
    return {
        "stars": stars,
        "passed": passed,
        "total": total,
        "ratio": round(ratio, 4),
        "soft_misses": misses,
        "action": action,
    }
