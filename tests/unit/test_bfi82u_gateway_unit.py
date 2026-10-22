"""sources/twse/bfi82u.py 與 get_market_institutional_amounts_history 的單元測試（不打網路）。

title、欄位與資料列取自證交所真實回應（2025-01-03 日報、2010-01-04 週報）；上游真實格式由
tests/contract/test_history_tier1_api.py::TestMarketInstitutionalAmountsGateway 驗證。
"""

import pytest

from sources.twse.bfi82u import institutional_amounts
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import institutional_amounts as institutional_amounts_tool
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["單位名稱", "買進金額", "賣出金額", "買賣差額"]
DAY = [["自營商(自行買賣)", "4,161,637,637", "4,078,689,337", "82,948,300"],
       ["自營商(避險)", "12,981,346,419", "11,881,741,939", "1,099,604,480"],
       ["投信", "11,274,678,554", "10,343,668,429", "931,010,125"],
       ["外資及陸資(不含外資自營商)", "111,929,269,350", "102,761,140,210", "9,168,129,140"],
       ["外資自營商", "0", "0", "0"],
       ["合計", "140,346,931,960", "129,065,239,915", "11,281,692,045"]]
WEEK = [["自營商", "24,722,775,456", "24,401,341,637", "321,433,819"],
        ["投信", "20,406,201,430", "21,941,268,478", "-1,535,067,048"],
        ["外資及陸資", "146,105,685,772", "96,648,425,178", "49,457,260,594"],
        ["合計", "191,234,662,658", "142,991,035,293", "48,243,627,365"]]
NO_DATA = {"stat": "很抱歉，沒有符合條件的資料!"}


def reply(rows=None, title="114年01月03日 三大法人買賣金額統計表", date="20250103", fields=None):
    return {"stat": "OK", "date": date, "title": title, "fields": fields or FIELDS, "data": DAY if rows is None else rows}


WEEK_REPLY = reply(WEEK, "099年01月04日至099年01月08日 三大法人買賣金額統計表", "20100104")


def _client(payload):
    return OfflineClient({"/fund/BFI82U": payload})


def test_rows_become_amounts():
    report = institutional_amounts(_client(reply()), "day", "20250103")
    assert (report.date, report.title) == ("20250103", "114年01月03日 三大法人買賣金額統計表")
    total = report.amounts[-1]
    assert (total.name, total.buy, total.sell, total.net) == ("合計", 140346931960, 129065239915, 11281692045)
    assert institutional_amounts(_client(WEEK_REPLY), "week", "20100104").amounts[1].net == -1535067048


def test_period_parameters():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return reply()

    client = _client(route)
    institutional_amounts(client, "day")
    institutional_amounts(client, "day", "20250103")
    institutional_amounts(client, "week", "20250106")
    institutional_amounts(client, "month", "20250103")
    assert seen == [{"response": "json", "type": "day"},
                    {"response": "json", "type": "day", "dayDate": "20250103"},
                    {"response": "json", "type": "week", "weekDate": "20250106"},
                    {"response": "json", "type": "month", "monthDate": "20250103"}]


def test_no_data_and_changed_fields():
    assert institutional_amounts(_client(NO_DATA), "week", "20180101") is None
    assert institutional_amounts(_client(reply([])), "day", "20260927") is None
    with pytest.raises(UpstreamFormatError, match="買賣差額"):
        institutional_amounts(_client(reply(fields=FIELDS[:3] + ["買賣超"])), "day", "20250103")
    with pytest.raises(UpstreamFormatError, match="3 欄"):
        institutional_amounts(_client(reply([DAY[0][:3]])), "day", "20250103")


def _tool(payload):
    return register_module_tools(institutional_amounts_tool, _client(payload))["get_market_institutional_amounts_history"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())(date="20250103")
    assert text.startswith("【114年01月03日 三大法人買賣金額統計表】（單位：億元）\n\n"
                           "自營商(自行買賣)：買進 41.62 億 | 賣出 40.79 億 | 買賣差額 0.83 億（82,948,300 元）\n")
    assert text.endswith("合計：買進 1,403.47 億 | 賣出 1,290.65 億 | 買賣差額 112.82 億（11,281,692,045 元）")


def test_week_falls_forward_to_its_first_trading_day_and_month_asks_the_latest_day_first():
    seen = []

    def route(params, _body):
        seen.append(params.get("weekDate") or params.get("monthDate") or params.get("dayDate"))
        if params["type"] == "week" and params["weekDate"] != "20100105":
            return NO_DATA
        return WEEK_REPLY

    fn = _tool(route)
    assert "099年01月04日至099年01月08日" in fn(date="20100107", period="week")
    assert seen == ["20100104", "20100105"]  # 週一沒有資料 → 週二
    seen.clear()
    fn(period="month")
    assert seen == [None, "20100104"]  # 先取最新交易日，再以它查該月
    assert "請確認該日期為交易日" in _tool(NO_DATA)(date="20260927")
