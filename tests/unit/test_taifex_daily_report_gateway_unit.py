"""sources/taifex/download.py、sources/taifex/daily_report.py 與期貨／選擇權每日行情工具的單元測試（不打網路）。

上游真實格式由 tests/contract/test_taifex_history_api.py 的 TestFuturesDailyGateway / TestOptionsDailyGateway 驗證。
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from sources.taifex.daily_report import futures_quotes, has_regular_session, option_quotes
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.taifex import daily_market_report
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FUT_HEADER = ["交易日期", "契約", "到期月份(週別)", "開盤價", "最高價", "最低價", "收盤價", "漲跌價", "漲跌%", "成交量",
              "結算價", "未沖銷契約數", "最後最佳買價", "最後最佳賣價", "歷史最高價", "歷史最低價", "是否因訊息面暫停交易",
              "交易時段", "價差對單式委託成交量"]
FUT_ROWS = [
    ["2025/01/03", "TX", "202501  ", "22935", "23108", "22905", "22977", "134", "0.59%", "62488", "22977", "71366",
     "22976", "22980", "23996", "22039", "", "一般", "", ""],
    ["2025/01/03", "TX", "202501/202502     ", "-", "-", "-", "-", "-", "-", "0", "-", "-", "40", "45", "-", "-", "",
     "一般", "", ""],
]
# optDataDown: 履約價 / 買賣權 after 到期月份, 漲跌 at the end, a trailing comma in the header
OPT_HEADER = ["交易日期", "契約", "到期月份(週別)", "履約價", "買賣權", "開盤價", "最高價", "最低價", "收盤價", "成交量",
              "結算價", "未沖銷契約數", "最後最佳買價", "最後最佳賣價", "歷史最高價", "歷史最低價", "是否因訊息面暫停交易",
              "交易時段", "漲跌價", "漲跌%", ""]
OPT_ROWS = [
    ["2025/01/03", "TXO", "202501W2", "20500.0000", "買權", "-", "-", "-", "-", "0", "2460", "0", "2450", "2480", "-",
     "-", "", "一般", "-", "-"],
    ["2025/01/03", "TXO", "202501  ", "23000.0000", "賣權", "120", "150", "0.1", "135", "8765", "136", "4321", "134",
     "136", "980", "0.1", "", "盤後", "-9.5", "-6.57%"],
]


def _csv(header, rows) -> bytes:
    return ("\r\n".join(",".join(r) for r in [header] + rows) + "\r\n").encode("cp950")


def _client(path, body):
    return OfflineClient({f"/cht/3/{path}": body})


START = END = datetime(2025, 1, 3)


def test_futures_rows_become_typed_quotes():
    quotes = futures_quotes(_client("futDataDown", _csv(FUT_HEADER, FUT_ROWS)), "TX", START, END)
    front, spread = quotes
    assert (front.day, front.contract, front.month, front.session) == (date(2025, 1, 3), "TX", "202501", "一般")
    assert (front.close, front.change, front.change_pct, front.volume, front.open_interest) == (
        Decimal("22977"), Decimal("134"), "0.59%", 62488, 71366)
    assert (spread.month, spread.close, spread.settlement, spread.volume) == ("202501/202502", None, None, 0)


def test_option_rows_become_typed_quotes():
    untraded, traded = option_quotes(_client("optDataDown", _csv(OPT_HEADER, OPT_ROWS)), "TXO", START, END)
    assert (untraded.strike, untraded.call_put, untraded.close, untraded.volume) == (Decimal("20500.0000"), "買權", None, 0)
    assert (traded.low, traded.best_ask, traded.session) == (Decimal("0.1"), Decimal("136"), "盤後")


def test_columns_are_found_by_name():
    # 交易日期 stays first: decode_and_parse_csv drops rows whose first cell is blank
    order = [0] + list(range(1, len(FUT_HEADER)))[::-1]
    header = [FUT_HEADER[i] for i in order]
    rows = [[r[i] for i in order] for r in FUT_ROWS]
    client = _client("futDataDown", _csv(FUT_HEADER, FUT_ROWS))
    assert futures_quotes(_client("futDataDown", _csv(header, rows)), "TX", START, END) == futures_quotes(client, "TX", START, END)


def test_renamed_column_or_changed_date_is_an_error():
    with pytest.raises(UpstreamFormatError, match="結算價"):
        futures_quotes(_client("futDataDown", _csv(FUT_HEADER[:10] + ["結算"] + FUT_HEADER[11:], FUT_ROWS)), "TX", START, END)
    with pytest.raises(UpstreamFormatError, match="日期格式"):
        futures_quotes(_client("futDataDown", _csv(FUT_HEADER, [["20250103"] + FUT_ROWS[0][1:]])), "TX", START, END)


def test_html_page_means_no_data():
    html = b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">\r\n<head></head>\r\n'
    assert futures_quotes(_client("futDataDown", html), "TX", START, END) is None


def test_form_fields():
    forms = []

    def route(_params, form):
        forms.append(dict(form))
        return _csv(FUT_HEADER, FUT_ROWS)

    futures_quotes(OfflineClient({"/cht/3/futDataDown": route}), "all", datetime(2025, 1, 2), datetime(2025, 1, 3))
    assert forms == [{"queryStartDate": "2025/01/02", "queryEndDate": "2025/01/03", "down_type": "1",
                      "commodity_id": "all", "commodity_id2": ""}]


def test_a_day_is_complete_once_its_regular_session_is_in():
    quotes = futures_quotes(_client("futDataDown", _csv(FUT_HEADER, FUT_ROWS)), "TX", START, END)
    assert has_regular_session(quotes)
    assert not has_regular_session([q for q in quotes if q.session == "盤後"])


def _tools(path, header, rows):
    return register_module_tools(daily_market_report, _client(path, _csv(header, rows)))


def test_futures_tool_prints_the_same_line_as_before_the_gateway():
    text = _tools("futDataDown", FUT_HEADER, FUT_ROWS)["get_daily_futures_market_report"]("TX", "20250103")
    assert ("2025/01/03 | 202501 | 一般 | 開:22935 高:23108 低:22905 收:22977 | 漲跌:134(0.59%) | 量:62488 | "
            "結算:22977 | 未平倉:71366 | 最佳買/賣:22976/22980") in text
    assert "202501/202502" not in text and "共 1 筆" in text  # 沒成交的價差組合不列


def test_options_tool_prints_the_same_line_as_before_the_gateway():
    fn = _tools("optDataDown", OPT_HEADER, OPT_ROWS)["get_daily_options_market_report"]
    chain = fn("TXO", "20250103", contract_month="202501W2")
    assert ("2025/01/03 | 202501W2 買權 履約:20500.0000 | 一般 | 開:- 高:- 低:- 收:- | 量:0 | 結算:2460 | 未平倉:0 | "
            "最佳買/賣:2450/2480") in chain
    top = fn("TXO", "20250103")
    assert "履約:23000.0000 | 盤後 | 開:120 高:150 低:0.1 收:135 | 量:8765" in top and "20500" not in top
