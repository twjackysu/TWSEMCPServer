"""期貨盤中走勢、股票代號轉股票期貨、選擇權月統計的離線測試（不打網路）。

上游介面由 tests/contract/test_taifex_history_api.py、test_taifex_batch2_api.py 驗證。
"""

import io
import zipfile

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.taifex import daily_market_report, intraday, trading_statistics

pytestmark = pytest.mark.offline

TICK_HEADER = "成交日期,商品代號,到期月份(週別),成交時間,成交價格,成交數量(B+S),近月價格,遠月價格,開盤集合競價"


def _zip(rows):
    lines = [TICK_HEADER] + [",".join(r) for r in rows]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Daily.csv", ("\r\n".join(lines) + "\r\n").encode("cp950"))
    return buf.getvalue()


def _tick(date, product, month, hhmmss, price, volume):
    return [date, f"{product}    ", f"{month}     ", hhmmss, str(price), str(volume), "-", "-", " "]


DAY_1016 = [
    # 夜盤：前一晚 15:00 起，跨過午夜
    _tick("20261015", "TX", "202610", "150000", 100, 20),
    _tick("20261015", "TX", "202610", "235958", 90, 10),
    _tick("20261016", "TX", "202610", "000130", 95, 4),
    # 日盤
    _tick("20261016", "TX", "202610", "084500", 100, 10),
    _tick("20261016", "TX", "202610", "084610", 104, 6),
    _tick("20261016", "TX", "202610", "085200", 98, 8),
    _tick("20261016", "TX", "202610", "134459", 101, 2),
    _tick("20261016", "TX", "202610", "134500", 102, 30),  # 收盤集合競價
    _tick("20261016", "TX", "202611", "090000", 105, 2),
    _tick("20261016", "TX", "202610/202611", "090000", 5, 100),  # 價差單，不計入
    _tick("20261016", "MTX", "202610", "090000", 100, 50),
    _tick("20261016", "CDF", "202610", "090000", 2400, 2),
    _tick("20261016", "QFF", "202610", "090000", 2401, 2),
    _tick("20261016", "QFF", "202610", "090100", 2402, 4),
]
NIGHT_ONLY_1019 = [_tick("20261016", "TX", "202610", "150000", 110, 2)]
PAGE = ('<a href="/file/taifex/Dailydownload/DailydownloadCSV/Daily_2026_10_19.zip">x</a>'
        '<a href="/file/taifex/Dailydownload/Dailydownload/Daily_2026_10_19.zip">rpt</a>'
        '<a href="/file/taifex/Dailydownload/DailydownloadCSV/Daily_2026_10_16.zip">x</a>').encode("utf-8")
SSF = [{"Contract": "CDF", "StockCode": "2330", "StockName": "台積電", "Type": "上市普通股標的證券"},
       {"Contract": "QFF", "StockCode": "2330", "StockName": "台積電", "Type": "上市普通股標的證券"}]


def _intraday_fn():
    client = OfflineClient({
        "dlFutPrevious30DaysSalesData": PAGE,
        "Daily_2026_10_16.zip": _zip(DAY_1016),
        "Daily_2026_10_19.zip": _zip(NIGHT_ONLY_1019),
        "/v1/SSFLists": SSF,
    })
    return register_module_tools(intraday, client)["get_futures_intraday"]


# ---------- parsing and bars ----------

def test_parse_ticks_filters_product_and_spreads_and_guards_header():
    text = "\r\n".join([TICK_HEADER] + [",".join(r) for r in DAY_1016])
    ticks = intraday.parse_ticks(text, "TX")
    assert len(ticks) == 9 and all("/" not in t[1] for t in ticks)
    assert intraday.available_days(PAGE.decode()) == ["20261019", "20261016"]
    with pytest.raises(ValueError, match="欄位已變更"):
        intraday.parse_ticks("日期,代號\n1,TX", "TX")


def test_bars_align_to_session_start_and_fold_closing_auction():
    ticks = intraday.parse_ticks("\r\n".join([TICK_HEADER] + [",".join(r) for r in DAY_1016]), "TX")
    day = [t for t in ticks if t[1] == "202610" and intraday.session_of(t[2]) == "day"]
    bars = intraday.build_bars(day, 5, intraday.DAY_START, intraday.DAY_END)
    assert [(b["minute"] // 60, b["minute"] % 60) for b in bars] == [(8, 45), (8, 50), (13, 40)]
    assert bars[0]["high"] == 104 and bars[-1]["close"] == 102 and bars[-1]["volume"] == 32
    thirty = intraday.build_bars(day, 30, intraday.DAY_START, intraday.DAY_END)
    assert [(b["minute"] // 60, b["minute"] % 60) for b in thirty] == [(8, 45), (13, 15)]
    night = [t for t in ticks if intraday.session_of(t[2]) == "night"]
    night_bars = intraday.build_bars(night, 60, intraday.NIGHT_START, intraday.NIGHT_END)
    assert [(b["date"], b["minute"] // 60) for b in night_bars] == [("20261015", 15), ("20261015", 23), ("20261016", 0)]


# ---------- get_futures_intraday ----------

def test_intraday_default_day_skips_file_with_only_night_session():
    text = _intraday_fn()()
    lines = text.splitlines()
    assert lines[0] == "【TX 202610 盤中走勢】交易日 2026-10-16｜日盤｜5 分K"
    assert "開 100（08:45:00）｜高 104（08:46:10）｜低 98（08:52:00）｜收 102（13:45:00）" in text
    assert "成交 28 口、5 筆" in text  # (10+6+8+2+30)/2
    assert "13:40 | 開 101 高 102 低 101 收 102 | 量 16 口" in text


def test_intraday_all_sessions_month_and_stock_code():
    fn = _intraday_fn()
    text = fn(date="20261016", session="all", interval=60)
    assert text.index("▍夜盤") < text.index("▍日盤")
    assert "成交 17 口、3 筆" in text  # 夜盤 (20+10+4)/2
    assert "【TX 202611 盤中走勢】" in fn(date="20261016", month="202611")
    assert "查無 TX 202612" in fn(date="20261016", month="202612")
    stock = fn(contract="2330", date="20261016")
    assert stock.startswith("【QFF 202610 盤中走勢】") and "2330 台積電 的股票期貨；另有 CDF" in stock  # QFF 筆數較多


def test_intraday_validation_and_listing():
    fn = _intraday_fn()
    assert "interval 必須是" in fn(interval=3)
    assert "session 必須是" in fn(session="morning")
    assert "只能查最近 30 個交易日：20261016～20261019" in fn(date="20250101")
    assert "CDF、MTX、QFF、TX" in fn(contract="", date="20261016")
    assert "查無 ZZZ" in fn(contract="ZZZ", date="20261016")


# ---------- get_daily_futures_market_report with a stock code ----------

FUT_HEADER = ["交易日期", "契約", "到期月份(週別)", "開盤價", "最高價", "最低價", "收盤價", "漲跌價", "漲跌%",
              "成交量", "結算價", "未沖銷契約數", "最後最佳買價", "最後最佳賣價", "歷史最高價", "歷史最低價",
              "是否因訊息面暫停交易", "交易時段", "價差對單式委託成交量"]


def _fut_csv(contract):
    row = ["2026/10/16", contract, "202610", "1", "2", "0", "1", "0", "0%", "9", "1", "5", "1", "2", "3", "0", "", "一般", ""]
    return ("\r\n".join([",".join(FUT_HEADER), ",".join(row)]) + "\r\n").encode("cp950")


def test_market_report_resolves_stock_code_to_every_stock_future():
    seen = []

    def fut_route(_params, form):
        seen.append(form["commodity_id"])
        return _fut_csv(form["commodity_id"])

    client = OfflineClient({"/cht/3/futDataDown": fut_route, "/v1/SSFLists": SSF})
    fn = register_module_tools(daily_market_report, client)["get_daily_futures_market_report"]
    text = fn(contract="2330", start_date="20261016")
    assert "【期貨每日交易行情】2330 台積電 股票期貨（CDF、QFF）" in text and "共 2 筆" in text
    assert "| CDF 202610 |" in text and "| QFF 202610 |" in text and seen == ["CDF", "QFF"]
    assert "9999 沒有股票期貨" in fn(contract="9999")
    assert "| 202610 |" in fn(contract="TX", start_date="20261016")  # 期貨代號照舊


# ---------- get_monthly_trading_statistics(market=) ----------

def test_monthly_statistics_market_switch():
    row = {"YYYYMM": "202609", "ContactName": "股價指數選擇權", "TotalVolume": "9", "MonthEndOpenInterest": "1"}
    client = OfflineClient({"/v1/MonthlyTradingStatisticsOptions": [row],
                            "/v1/MonthlyTradingStatisticsFutures": [{**row, "ContactName": "股價指數期貨"}]})
    fn = register_module_tools(trading_statistics, client)["get_monthly_trading_statistics"]
    assert fn(market="options").startswith("【選擇權市場月統計】") and "股價指數選擇權" in fn(market="options")
    assert fn().startswith("【期貨市場月統計】")
    assert "market 必須是 futures、options" in fn(market="stock")
