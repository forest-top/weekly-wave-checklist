"""Close-only main-board scanner. Uses public quote/K-line endpoints with stdlib only."""

import argparse
import datetime as dt
import json
import math
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from .scoring import SOFT_KEYS, score_candidate
except ImportError:
    from scoring import SOFT_KEYS, score_candidate

HEADERS = {"User-Agent": "Mozilla/5.0 weekly-wave-checklist"}
TODAY_CN = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)).date().isoformat()
MIN_MAIN_BOARD_UNIVERSE = 2500


def fetch_json(url, retries=3):
    request = urllib.request.Request(url, headers=HEADERS)
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:  # external data source: retry before dropping a symbol
            last_error = error
            time.sleep(0.4 * (attempt + 1))
    raise last_error


def is_main_board(code):
    code = str(code or "").strip()
    return (code.startswith(("000", "001", "002", "003")) or code.startswith(("600", "601", "603", "605"))) and len(code) == 6


def select_scope(stocks, limit=0):
    main_board = [stock for stock in stocks if is_main_board(stock.get("f12"))]
    return main_board if limit <= 0 else main_board[:limit]


def validate_main_board_scope(stocks):
    if len(stocks) < MIN_MAIN_BOARD_UNIVERSE:
        raise RuntimeError(f"main-board quote universe is incomplete: {len(stocks)} stocks found")
    return stocks


def fetch_quotes(pages):
    fields = "f12,f14,f2,f3,f6,f8,f20,f23"
    fs = "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23"
    stocks = []
    for page in range(1, pages + 1):
        params = {"pn": page, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f6", "fs": fs, "fields": fields}
        url = "https://push2.eastmoney.com/api/qt/clist/get?" + urllib.parse.urlencode(params)
        try:
            payload = fetch_json(url).get("data", {})
            rows = payload.get("diff", [])
        except Exception as error:
            raise RuntimeError(f"quote page {page} is unavailable") from error
        if not rows:
            expected_pages = math.ceil(int(payload.get("total") or 0) / 100)
            if expected_pages and page <= min(pages, expected_pages):
                raise RuntimeError(f"quote page {page} returned no data before the expected end")
            break
        stocks.extend(rows)
    return validate_main_board_scope(select_scope(stocks))


def fetch_kline(code):
    symbol = str(code) if str(code).startswith(("sh", "sz")) else ("sh" if str(code).startswith("6") else "sz") + str(code)
    params = urllib.parse.urlencode({"param": f"{symbol},day,,,900,qfq"})
    payload = fetch_json("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?" + params).get("data", {}).get(symbol, {})
    rows = payload.get("qfqday") or payload.get("day") or []
    return [row for row in rows if row and row[0] <= TODAY_CN]


def average(values, window):
    return sum(values[-window:]) / window


def ema(values, window):
    current = values[0]
    factor = 2 / (window + 1)
    for value in values[1:]:
        current = value * factor + current * (1 - factor)
    return current


def weekly_rows(rows):
    result = []
    current = None
    current_key = None
    for row in rows:
        date, open_, close, high, low, volume = row[:6]
        year, week, _ = dt.date.fromisoformat(date).isocalendar()
        key = (year, week)
        if key != current_key:
            if current:
                result.append(current)
            current_key = key
            current = [date, float(open_), float(close), float(high), float(low), float(volume)]
        else:
            current[0] = date
            current[2] = float(close)
            current[3] = max(current[3], float(high))
            current[4] = min(current[4], float(low))
            current[5] += float(volume)
    if current:
        result.append(current)
    return result


def weekly_macd(closes):
    difs = []
    for index in range(26, len(closes) + 1):
        sample = closes[:index]
        difs.append(ema(sample, 12) - ema(sample, 26))
    dif = difs[-1]
    dea = ema(difs, 9)
    return dif, dea, (dif - dea) * 2


def evaluate(stock, market):
    code = str(stock["f12"])
    if str(stock.get("f14") or "").upper().startswith(("ST", "*ST")):
        return None
    rows = fetch_kline(code)
    if len(rows) < 300:
        return None
    closes = [float(row[2]) for row in rows]
    volumes = [float(row[5]) for row in rows]
    price = closes[-1]
    ma5, ma13, ma20, ma55 = (average(closes, n) for n in (5, 13, 20, 55))
    ma13_old = sum(closes[-18:-5]) / 13
    ma55_old = sum(closes[-60:-5]) / 55
    weeks = weekly_rows(rows)
    weekly_closes = [row[2] for row in weeks]
    if len(weekly_closes) < 60:
        return None
    w5, w13, w55 = (average(weekly_closes, n) for n in (5, 13, 55))
    dif, dea, histogram = weekly_macd(weekly_closes)
    prior_high = max(closes[-81:-21])
    wave_low = min(weekly_closes[-40:])
    wave_high = max(weekly_closes[-26:])
    wave_span = max(wave_high - wave_low, 0.0001)
    retracement = (wave_high - weekly_closes[-1]) / wave_span
    five_day_return = price / closes[-6] - 1
    volume_ratio = average(volumes[-5:], 5) / max(average(volumes[-25:-5], 20), 0.0001)
    bias5 = abs(price / ma5 - 1)
    bias13 = abs(price / ma13 - 1)
    pb_value = stock.get("f23")
    try:
        pb_value = float(pb_value)
    except (TypeError, ValueError):
        pb_value = None
    conditions = {
        "board_proxy": five_day_return > market["five_day_return"] and price > ma20,
        "daily_trend": ma13 > ma13_old and ma55 > ma55_old and ma13 > ma55,
        "weekly_trend": w5 > w13 > w55,
        "weekly_macd": dif > 0 and histogram > 0,
        "wave_structure": price > wave_low * 1.15 and price < prior_high * 1.18,
        "wave_retracement": 0.2 <= retracement <= 0.7 and weekly_closes[-1] > wave_low,
        "valuation": pb_value is not None and pb_value <= 22,
        "entry_bias": min(bias5, bias13) <= 0.03,
        "ma_gap": 0.05 <= abs(ma5 / ma13 - 1) <= 0.15,
        "pullback": rows[-1][2] <= rows[-2][2] * 1.03 and price >= ma13 * 0.97,
        "volume": volume_ratio <= 1.3,
        "not_extended": price <= prior_high * 1.18,
    }
    scored = score_candidate({**conditions, "main_board": True, "data_complete": True, "market_gate": market["gate"]})
    passed = [key for key in SOFT_KEYS if conditions[key]]
    failed = [key for key in SOFT_KEYS if not conditions[key]]
    labels = {
        "board_proxy": "相对大盘强度/MA20代理通过", "daily_trend": "日线均线趋势通过", "weekly_trend": "周线多头排列通过",
        "weekly_macd": "周MACD通过", "wave_structure": "浪形未明显赶顶", "wave_retracement": "回撤区间合理",
        "valuation": "PB估值通过", "entry_bias": "乖离率通过", "ma_gap": "MA5/MA13距离通过",
        "pullback": "回踩位置通过", "volume": "量能没有异常放大", "not_extended": "未明显脱离前高",
    }
    reasons = [labels[key] for key in passed]
    reasons.extend(f"待确认：{labels[key]}" for key in failed)
    return {
        "code": code,
        "name": stock["f14"],
        "price": round(price, 2),
        "pb": round(pb_value, 2) if pb_value is not None else None,
        "amount_yi": round(float(stock.get("f6") or 0) / 1e8, 2),
        "market_cap_yi": round(float(stock.get("f20") or 0) / 1e8, 1),
        "ma5": round(ma5, 2), "ma13": round(ma13, 2), "ma55": round(ma55, 2),
        "bias": round(min(bias5, bias13) * 100, 2), "ma_gap": round(abs(ma5 / ma13 - 1) * 100, 2),
        "five_day_return": round(five_day_return * 100, 2), "volume_ratio": round(volume_ratio, 2),
        "support": round(max(ma13, min(closes[-21:])), 2), "stop_3pct": round(price * 0.97, 2),
        "conditions": conditions, "passed": passed, "failed": failed, "reasons": reasons, **scored,
    }


def build_report(pages, limit):
    index_rows = fetch_kline("sh000001")
    index_closes = [float(row[2]) for row in index_rows]
    index_ma55 = average(index_closes, 55)
    index_ma55_old = sum(index_closes[-60:-5]) / 55
    market = {
        "last_complete_date": index_rows[-1][0],
        "close": round(index_closes[-1], 2),
        "ma55": round(index_ma55, 2),
        "ma55_slope_5d_pct": round((index_ma55 / index_ma55_old - 1) * 100, 3),
        "gate": index_closes[-1] > index_ma55 and index_ma55 > index_ma55_old,
        "five_day_return": index_closes[-1] / index_closes[-6] - 1,
    }
    all_stocks = fetch_quotes(pages)
    stocks = select_scope(all_stocks, limit)
    results = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(evaluate, stock, market) for stock in stocks]
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                continue
    results.sort(key=lambda row: (row["stars"], row["ratio"], row["amount_yi"]), reverse=True)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "data_date": index_rows[-1][0],
        "universe": len(stocks),
        "main_board_total": len(all_stocks),
        "bars_attempted": len(stocks),
        "market": market,
        "soft_rule": "12个软条件；5星=100%，4星>=90%，3星>=80%；最多容忍2个软缺口，3个及以上放弃。大盘闸门为硬条件。",
        "proxy_note": "板块条件使用个股相对大盘强度和MA20代理，最终下单前仍需人工确认行业强度。",
        "complete_matches": [row for row in results if row["stars"] == 5],
        "candidates": results[:50],
        "status": "ok",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=60)
    parser.add_argument("--limit", type=int, default=0, help="0 scans every main-board quote; positive values are test caps")
    parser.add_argument("--output", default="data/latest.json")
    args = parser.parse_args()
    report = build_report(args.pages, args.limit)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"status": report["status"], "universe": report["universe"], "candidates": len(report["candidates"]), "complete": len(report["complete_matches"]), "market_gate": report["market"]["gate"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
