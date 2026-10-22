"""sources/twse/fmsrfk.py、sources/twse/fmnptk.py 與 get_stock_monthly_trading／get_stock_yearly_trading 的單元測試
（不打網路）。

欄位與資料列取自證交所真實回應（2330 的 2025 年逐月、2330 歷年）；上游真實格式由
tests/contract/test_history_tier2_api.py 的 TestMonthlyTradingGateway / TestYearlyTradingGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.twse.fmnptk import yearly_trading
from sources.twse.fmsrfk import monthly_trading
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import stock_monthly_yearly_history
from utils.date_helper import taipei_today
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

MONTH_FIELDS = ["年度", "月份", "最高價", "最低價", "加權(A/B)平均價", "成交筆數", "成交金額(A)", "成交股數(B)", "週轉率(%)"]
MONTHS = [[114, 1, "1,160.00", "1,055.00", "1,105.45", "919,543", "726,797,248,009", "657,463,196", "2.53"],
          [114, 12, "1,550.00", "1,410.00", "1,465.93", "1,367,411", "880,294,126,428", "600,500,270", "2.31"]]
YEAR_FIELDS = ["年度", "成交股數", "成交金額", "成交筆數", "最高價", "日期", "最低價", "日期", "收盤平均價"]
YEARS = [[83, "260,767,893", "43,077,714,614", "90,627", "177.00", "10/05", "96.00", "9/05", "159.04"],
         [114, "8,999,950,601", "10,296,188,010,790", "18,620,227", "1,550.00", "12/31", "780.00", "4/09", "1,163.06"]]
NOT_FOUND = {"stat": "很抱歉，沒有符合條件的資料!"}


def month_reply(rows=None, fields=None):
    return {"stat": "OK", "date": "20250103", "title": "114年2330 台積電           月成交資訊",
            "fields": fields or MONTH_FIELDS, "data": MONTHS if rows is None else rows}


def year_reply(rows=None, fields=None):
    return {"stat": "OK", "tables": [
        {"title": "2330 台積電           年度 成交資訊", "fields": fields or YEAR_FIELDS, "data": YEARS if rows is None else rows},
        {"fields": ["近年最高價", "日期", "近年最低價", "日期"], "data": [["1,550.00", "114/12/31", "34.90", "91/10/08"]]}]}


def _client(path, payload):
    return OfflineClient({f"/afterTrading/{path}": payload})


def test_monthly_rows_become_typed_months():
    year = monthly_trading(_client("FMSRFK", month_reply()), "2330", "20250103")
    jan = year.months[0]
    assert year.title == "114年2330 台積電           月成交資訊"
    assert (jan.year, jan.month, jan.high, jan.low, jan.average) == (
        114, 1, Decimal("1160.00"), Decimal("1055.00"), Decimal("1105.45"))
    assert (jan.transactions, jan.value, jan.volume, jan.turnover) == (919543, 726797248009, 657463196, Decimal("2.53"))


def test_yearly_rows_name_each_date_after_its_price():
    first, last = yearly_trading(_client("FMNPTK", year_reply()), "2330", "20261022")
    assert (first.year, first.high, first.high_date, first.low, first.low_date) == (
        83, Decimal("177.00"), "10/05", Decimal("96.00"), "9/05")
    assert (last.volume, last.value, last.transactions, last.average_close) == (
        8999950601, 10296188010790, 18620227, Decimal("1163.06"))


def test_requests_no_data_and_changed_replies():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return month_reply()

    monthly_trading(_client("FMSRFK", route), "2330")
    assert seen == [{"response": "json", "stockNo": "2330"}]
    assert monthly_trading(_client("FMSRFK", NOT_FOUND), "9999") is None
    assert yearly_trading(_client("FMNPTK", NOT_FOUND), "9999", "20261022") is None
    with pytest.raises(UpstreamFormatError, match="週轉率"):
        monthly_trading(_client("FMSRFK", month_reply(fields=MONTH_FIELDS[:8] + ["週轉率"])), "2330", "20250103")
    # 日期 no longer right after 最低價: the low's date cannot be told apart
    moved = YEAR_FIELDS[:6] + ["日期", "最低價", "收盤平均價"]
    with pytest.raises(UpstreamFormatError, match="最低價/日期"):
        yearly_trading(_client("FMNPTK", year_reply(fields=moved)), "2330", "20261022")
    with pytest.raises(UpstreamFormatError, match="年度"):
        monthly_trading(_client("FMSRFK", month_reply([["114年"] + MONTHS[0][1:]])), "2330", "20250103")


def _tools(path, payload):
    return register_module_tools(stock_monthly_yearly_history, _client(path, payload))


def test_monthly_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tools("FMSRFK", month_reply())["get_stock_monthly_trading"]("2330", "20250103")
    assert text == ("【114年2330 台積電           月成交資訊】\n\n"
                    "114/01 | 最高:1,160.00 最低:1,055.00 加權均價:1,105.45 | 量:657,463,196 金額:726,797,248,009 "
                    "筆數:919,543 | 週轉率:2.53%\n"
                    "114/12 | 最高:1,550.00 最低:1,410.00 加權均價:1,465.93 | 量:600,500,270 金額:880,294,126,428 "
                    "筆數:1,367,411 | 週轉率:2.31%")
    assert "請確認代號是否正確" in _tools("FMSRFK", NOT_FOUND)["get_stock_monthly_trading"]("9999")


def test_yearly_tool_prints_the_same_lines_and_asks_up_to_today():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return year_reply()

    text = _tools("FMNPTK", route)["get_stock_yearly_trading"]("2330")
    # FMNPTK ends the series with the year of date: a fixed date would drop every later year without a trace
    assert seen[0]["date"] == f"{taipei_today():%Y%m%d}"
    assert text.startswith("【2330 歷年成交資訊】（共 2 年）\n\n"
                           "83年 | 最高:177.00（10/05） 最低:96.00（9/05） 收盤均價:159.04 | "
                           "量:260,767,893 金額:43,077,714,614 筆數:90,627\n")
    assert "請確認代號是否正確" in _tools("FMNPTK", NOT_FOUND)["get_stock_yearly_trading"]("9999")
