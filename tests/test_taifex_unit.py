"""utils/taifex.py 與改用下載頁的 TAIFEX 工具之單元測試（不打網路）。

下載頁的欄位順序與行為由 tests/e2e/test_taifex_history_api.py 驗證；這裡測我們自己的邏輯：
最新交易日往回找、HTML／空白列處理、cp950 解碼、契約代碼與中文名稱的篩選、價差列與成交量排序、
大額交易人月份標籤。
"""

from datetime import datetime

import pytest

import utils.taifex as taifex
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.taifex import daily_market_report, institutional_details, large_traders_oi

pytestmark = pytest.mark.offline

TODAY = datetime(2026, 9, 30)  # 星期三


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr(taifex, "taipei_today", lambda: TODAY)


def _csv(header, rows) -> bytes:
    lines = [",".join(header)] + [",".join(r) for r in rows]
    return ("\r\n".join(lines) + "\r\n").encode("cp950")


HTML_NO_DATA = b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">\r\n\r\n<head></head>\r\n\r\n'


# ---------- decode_and_parse_csv ----------

def test_doctype_html_page_means_no_data():
    """無資料日回的是 <!DOCTYPE HTML ...> 頁，以前只認 <html 開頭，會被當成一欄 CSV 解析."""
    assert taifex.decode_and_parse_csv(HTML_NO_DATA) is None


def test_blank_lines_are_skipped_and_cp950_characters_decode():
    body = _csv(["日期", "商品(契約)", "商品名稱"], [["2026/09/29", "DS", "宏碁期貨"]]) + b"\r\n\r\n"
    header, rows = taifex.decode_and_parse_csv(body)
    assert rows == [["2026/09/29", "DS", "宏碁期貨"]]


@pytest.mark.parametrize("value,expected", [("TXF", True), ("tx", True), ("臺股期貨", False), ("", False)])
def test_is_contract_code(value, expected):
    assert taifex.is_contract_code(value) is expected


# ---------- fetch_period ----------

def test_latest_walks_back_until_a_day_has_data():
    asked = []

    def fetch(start_dt, end_dt):
        asked.append(start_dt)
        return (["h"], [["2026/09/29"]]) if start_dt == datetime(2026, 9, 29) else None

    parsed, label, error = taifex.fetch_period(fetch, "", "", 31, "20260601")
    assert error is None and parsed[1] == [["2026/09/29"]]
    assert asked == [datetime(2026, 9, 30), datetime(2026, 9, 29)]
    assert label.startswith("20260929")


def test_latest_skips_a_partial_day():
    def fetch(start_dt, end_dt):
        session = "盤後" if start_dt == TODAY else "一般"
        return ["h"], [[f"{start_dt:%Y/%m/%d}"] + [""] * 16 + [session]]

    parsed, label, _ = taifex.fetch_period(
        fetch, "", "", 31, "20260601", is_complete=daily_market_report.has_regular_session
    )
    assert label.startswith("20260929")


def test_latest_gives_up_after_the_lookback_window():
    calls = []
    parsed, label, error = taifex.fetch_period(lambda s, e: calls.append(s), "", "", 31, "20260601")
    assert parsed is None and error is None and len(calls) == taifex.LATEST_LOOKBACK_DAYS


def test_single_date_and_invalid_range():
    seen = []
    taifex.fetch_period(lambda s, e: seen.append((s, e)), "20260803", "", 31, "20260601")
    assert seen == [(datetime(2026, 8, 3), datetime(2026, 8, 3))]
    _parsed, _label, error = taifex.fetch_period(lambda s, e: None, "20260101", "20260301", 31, "20260601")
    assert "不可超過 31 天" in error


# ---------- daily market report ----------

FUT_HEADER = ["交易日期", "契約", "到期月份(週別)", "開盤價", "最高價", "最低價", "收盤價", "漲跌價", "漲跌%",
              "成交量", "結算價", "未沖銷契約數", "最後最佳買價", "最後最佳賣價", "歷史最高價", "歷史最低價",
              "是否因訊息面暫停交易", "交易時段", "價差對單式委託成交量"]


def _fut_row(contract, month, volume, session="一般"):
    return ["2026/09/29", contract, month, "1", "2", "0", "1", "0", "0%", volume, "1", "5", "1", "2",
            "3", "0", "", session, ""]


def _fut_route(form_seen):
    def route(_params, form):
        form_seen.append(dict(form))
        if form["queryStartDate"] != "2026/09/29":
            return HTML_NO_DATA
        rows = [_fut_row("TX", "202610", "100"), _fut_row("TX", "202610/202611", "0"),
                _fut_row("TX", "202610/202612", "3"), _fut_row("MTX", "202610", "50")]
        if form["commodity_id"] != "all":
            rows = [r for r in rows if r[1] == form["commodity_id"]]
        return _csv(FUT_HEADER, rows)
    return route


def test_futures_report_drops_untraded_spreads_and_lists_contracts():
    seen = []
    tools = register_module_tools(daily_market_report, OfflineClient({"/cht/3/futDataDown": _fut_route(seen)}))
    text = tools["get_daily_futures_market_report"]()
    assert "20260929（最新交易日）" in text and "共 2 筆" in text
    assert "202610/202611" not in text and "202610/202612" in text
    listing = tools["get_daily_futures_market_report"](contract="")
    assert "TX" in listing and "MTX" in listing and seen[-1]["commodity_id"] == "all"


OPT_HEADER = FUT_HEADER[:3] + ["履約價", "買賣權"] + FUT_HEADER[3:7] + FUT_HEADER[9:18]


def _opt_row(month, strike, cp, volume, date="2026/09/29"):
    return [date, "TXO", month, strike, cp, "1", "2", "0", "1", volume, "1", "5", "1", "2", "3", "0", "", "一般"]


def test_options_report_takes_top_volume_per_day_or_full_month_chain():
    rows = [_opt_row("202610", "48000", "買權", "5"), _opt_row("202610", "48100", "買權", "50"),
            _opt_row("202610", "48200", "賣權", "0"), _opt_row("202611", "48000", "賣權", "20")]
    tools = register_module_tools(daily_market_report, OfflineClient({"/cht/3/optDataDown": _csv(OPT_HEADER, rows)}))
    fn = tools["get_daily_options_market_report"]
    text = fn(start_date="20260929", limit=2)
    body = text.split("\n\n", 1)[1]
    assert body.index("48100") < body.index("202611") and "48200" not in body  # 依量排序、只列有成交
    assert "可用到期月份：202610、202611" in text
    chain = fn(start_date="20260929", contract_month="202610")
    assert "共 3 筆" in chain and "48200" in chain


# ---------- institutional details ----------

INST_HEADER = ["日期", "商品名稱", "身份別"] + [f"n{i}" for i in range(12)]


def _inst_route(forms):
    def route(_params, form):
        forms.append(dict(form))
        rows = [["2026/09/29", "臺股期貨", "外資及陸資"] + ["1"] * 12,
                ["2026/09/29", "小型臺指期貨", "外資及陸資"] + ["2"] * 12]
        return _csv(INST_HEADER, rows)
    return route


def test_contract_code_goes_to_server_and_chinese_name_is_filtered_locally():
    forms = []
    tools = register_module_tools(institutional_details, OfflineClient({"/cht/3/futContractsDateDown": _inst_route(forms)}))
    fn = tools["get_institutional_traders_by_futures"]
    fn("TXF", "20260929")
    assert forms[-1]["commodityId"] == "TXF"
    text = fn("小型臺指", "20260929")
    assert forms[-1]["commodityId"] == "" and "小型臺指期貨" in text and "▶ 2026/09/29 臺股期貨" not in text
    assert "可用契約：小型臺指期貨、臺股期貨" in fn("黃金", "20260929")


# ---------- large traders ----------

LT_HEADER = ["日期", "商品(契約)", "商品名稱(契約名稱)", "到期月份(週別)", "交易人類別",
             "前五大交易人買方", "前五大交易人賣方", "前十大交易人買方", "前十大交易人賣方", "全市場未沖銷部位數"]


def test_large_traders_labels_download_page_month_codes():
    rows = [["2026/09/29", "TX     ", "臺股期貨", "999999  ", "0", "1", "2", "3", "4", "5"],
            ["2026/09/29", "TX     ", "臺股期貨", "666666  ", "1", "1", "2", "3", "4", "5"],
            ["2026/09/29", "MTX    ", "小型臺指", "202610  ", "0", "1", "2", "3", "4", "5"]]
    tools = register_module_tools(large_traders_oi, OfflineClient({"/cht/3/largeTraderFutDown": _csv(LT_HEADER, rows)}))
    fn = tools["get_large_traders_futures_oi"]
    text = fn(start_date="20260929")
    assert "所有月份總計 | 所有交易人" in text and "所有月份合計 | 特定法人" in text and "MTX" not in text
    assert "MTX(小型臺指)" in fn(contract="", start_date="20260929")


LT_OPT_HEADER = ["日期", "商品(契約)", "商品名稱(契約名稱)", "買賣權", "到期月份(週別)", "交易人類別",
                 "前五大交易人買方", "前五大交易人賣方", "前十大交易人買方", "前十大交易人賣方", "全市場未沖銷部位數"]


def _lt_opt_route(forms):
    def route(_params, form):
        forms.append(dict(form))
        if form["queryStartDate"] != "2026/09/29":
            return HTML_NO_DATA
        rows = [["2026/09/29", "TXO    ", "臺指", "買權", "999999  ", "0", "1", "2", "3", "4", "5"],
                ["2026/09/29", "TXO    ", "臺指", "賣權", "202610  ", "1", "1", "2", "3", "4", "5"],
                ["2026/09/29", "CA     ", "南亞", "買權", "666666  ", "0", "1", "2", "3", "4", "5"]]
        return _csv(LT_OPT_HEADER, rows)
    return route


def test_large_traders_options_latest_day_filters_locally_and_labels_months():
    forms = []
    tools = register_module_tools(large_traders_oi, OfflineClient({"/cht/3/largeTraderOptDown": _lt_opt_route(forms)}))
    fn = tools["get_large_traders_options_oi"]
    text = fn()
    assert "20260929（最新交易日）" in text and "共 2 筆" in text and "CA" not in text
    assert "買權 | 所有月份總計 | 所有交易人" in text and "賣權 | 到期月 202610 | 特定法人" in text
    assert forms[0]["queryStartDate"] == forms[0]["queryEndDate"] == "2026/09/30"  # 從今天往回找
    assert "共 1 筆" in fn(call_put="賣權") and "查無契約 ZZZ" in fn(contract="ZZZ")


def test_large_traders_options_lists_contracts_and_validates_range():
    fn = register_module_tools(large_traders_oi, OfflineClient({"/cht/3/largeTraderOptDown": _lt_opt_route([])}))[
        "get_large_traders_options_oi"]
    assert "CA(南亞)、TXO(臺指)" in fn(contract="", start_date="20260929")
    assert "不可超過 31 天" in fn(start_date="20260101", end_date="20260301")
    # 舊的位置參數順序 (contract, call_put) 維持不變
    assert "共 1 筆" in fn("TXO", "買權", "20260929")
