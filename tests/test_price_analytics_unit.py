"""utils/indicators.py、utils/price_series.py 與 tools/analytics/price_tools.py 的單元測試（不打網路）。

指標數值用可以手算的小序列驗證；還原權息與市場判斷用 OfflineClient 餵假資料。
"""

from datetime import date

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.analytics import price_tools
from utils import indicators, price_series
from utils.price_series import Bar, ExRightEvent, adjust_bars, fetch_daily_bars, fetch_exright_events

pytestmark = pytest.mark.offline


# ---------- indicators ----------

def test_sma_and_ema_known_values():
    assert indicators.sma([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4]
    # EMA(3): 以前 3 筆 SMA=2 起算，k=0.5 → 3, 4
    assert indicators.ema([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4]


def test_rsi_wilder_known_values():
    # gains [1,1,0,1] losses [0,0,1,0]，n=2 → 100, 50, 75
    assert indicators.rsi([1, 2, 3, 2, 3], 2) == [None, None, 100.0, 50.0, 75.0]


def test_kd_seeded_at_50():
    rising = [1.0, 2.0, 3.0]
    k, d = indicators.kd(rising, rising, rising, n=2)
    assert k[0] is None
    assert k[1] == pytest.approx(50 * 2 / 3 + 100 / 3)
    assert d[1] == pytest.approx(50 * 2 / 3 + k[1] / 3)


def test_macd_and_bollinger_shapes():
    closes = [float(i) for i in range(1, 61)]
    dif, sig, osc = indicators.macd(closes)
    assert dif[24] is None and dif[25] is not None and sig[25 + 7] is None and sig[25 + 8] is not None
    assert osc[-1] == pytest.approx(dif[-1] - sig[-1])
    upper, mid, lower = indicators.bollinger([10.0] * 25)
    assert upper[-1] == mid[-1] == lower[-1] == 10.0 and upper[18] is None


# ---------- price series ----------

def _bar(d, close):
    return Bar(d, close, close, close, close, 1000)


def test_adjust_bars_multiplies_every_later_factor():
    bars = [_bar(date(2026, 6, 1), 100), _bar(date(2026, 7, 1), 100), _bar(date(2026, 8, 1), 100)]
    events = [ExRightEvent(date(2026, 6, 15), 100, 90, "息"), ExRightEvent(date(2026, 7, 15), 100, 80, "權")]
    adj = adjust_bars(bars, events)
    assert [b.close for b in adj] == [pytest.approx(72), pytest.approx(80), 100]
    assert adj[0].volume == 1000  # 成交量不調整


def _stock_day(params, _body):
    return {"stat": "很抱歉，沒有符合條件的資料!"}


def _trading_stock(params, _body):
    if params["date"] != "2026/09/01":
        return {"tables": [{"data": []}]}
    return {"name": "環球晶", "tables": [{"data": [["115/09/30", "18,766", "1", "966", "1,035", "953", "1,035", "90", "1"]]}]}


def test_market_detection_falls_back_to_otc_and_converts_lots_to_shares():
    client = OfflineClient({"/exchangeReport/STOCK_DAY": _stock_day, "/afterTrading/tradingStock": _trading_stock})
    market, name, bars = fetch_daily_bars(client, "6488", [(2026, 8), (2026, 9)])
    assert (market, name) == ("上櫃", "環球晶")
    assert bars == [Bar(date(2026, 9, 30), 966, 1035, 953, 1035, 18_766_000)]


def test_listed_detection_parses_name_and_skips_untraded_days():
    payload = {"stat": "OK", "title": "115年09月 2330 台積電           各日成交資訊",
               "data": [["115/09/29", "1,000", "1", "2,475.00", "2,495.00", "2,475.00", "2,475.00", "0", "1"],
                        ["115/09/30", "0", "0", "--", "--", "--", "--", "0", "0"]]}
    client = OfflineClient({"/exchangeReport/STOCK_DAY": payload})
    market, name, bars = fetch_daily_bars(client, "2330", [(2026, 9)])
    assert (market, name) == ("上市", "台積電")
    assert bars[0].close == 2475.0 and bars[1].close is None


def test_exright_events_for_both_markets():
    listed = {"stat": "OK", "data": [["115年06月11日", "2330", "台積電", "2,255.00", "2,248.99", "6.0", "息"],
                                     ["115年06月11日", "2317", "鴻海", "1", "1", "0", "息"]]}
    otc = {"tables": [{"data": [["115/07/01", "4116", "明基醫  ", "38.50", "36.50", "0", "2", "2", "除息"]]}]}
    client = OfflineClient({"/exRight/TWT49U": listed, "/bulletin/exDailyQ": otc})
    ev = fetch_exright_events(client, "上市", "2330", date(2026, 1, 1), date(2026, 12, 31))
    assert ev == [ExRightEvent(date(2026, 6, 11), 2255.0, 2248.99, "息")]
    ev = fetch_exright_events(client, "上櫃", "4116", date(2026, 1, 1), date(2026, 12, 31))
    assert ev[0].kind == "除息" and ev[0].factor == pytest.approx(36.5 / 38.5)


# ---------- tools ----------

@pytest.mark.parametrize("start,end,message", [
    ("2026-01", "", "格式錯誤"), ("202603", "202601", "不可晚於"), ("202501", "202601", "最多 12 個月"),
])
def test_month_argument_validation(start, end, message):
    fn = register_module_tools(price_tools, OfflineClient({}))["get_adjusted_price_history"]
    assert message in fn("2330", start, end)


def test_indicators_need_enough_history(monkeypatch):
    monkeypatch.setattr(price_tools, "fetch_daily_bars", lambda *_a: ("上市", "台積電", [_bar(date(2026, 9, 1), 1)] * 10))
    fn = register_module_tools(price_tools, OfflineClient({}))["get_technical_indicators"]
    assert "僅 10 個交易日" in fn("2330")


def test_months_back_crosses_year():
    assert price_series.months_back(3, date(2026, 2, 1)) == [(2025, 12), (2026, 1), (2026, 2)]
