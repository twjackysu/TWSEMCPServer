"""sources/twse/twtb4u.py 與 get_daily_day_trading_targets 的單元測試（不打網路）。

回應的形狀與欄位取自證交所真實回應（2025-01-03 收盤後、2026-10-22 盤中公布前）；上游真實格式由
tests/contract/test_history_tier3_api.py::TestDayTradingGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.twse.twtb4u import day_trading
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import exright_day_trading_indices
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

SUMMARY_FIELDS = ["當日沖銷交易總成交股數", "當日沖銷交易總成交股數占市場比重%", "當日沖銷交易總買進成交金額",
                  "當日沖銷交易總買進成交金額占市場比重%", "當日沖銷交易總賣出成交金額", "當日沖銷交易總賣出成交金額占市場比重%"]
SUMMARY = ["1,336,093,000", "21.55", "126,279,376,690", "37.46", "126,483,285,690", "37.52"]
TARGET_FIELDS = ["證券代號", "證券名稱", "暫停現股賣出後現款買進當沖註記", "當日沖銷交易成交股數", "當日沖銷交易買進成交金額",
                 "當日沖銷交易賣出成交金額"]
TARGETS = [["0050", "元大台灣50", "", "269,000", "52,719,950", "52,751,400"],
           ["00400A", "主動國泰動能高息", "Y", "1,000", "15,550", "15,600"]]
# Before the evening publication: an empty first table and the list only, 註記 written with a line break.
LIST_FIELDS = ["證券代號", "證券名稱", "暫停現股賣出後\n現款買進當沖註記"]
LIST = [["00400A", "主動國泰動能高息", ""], ["2330", "台積電", "Y"]]


def reply(summary=None, targets=None, date="20250103"):
    """A published day (the default) or, with ``summary=[]`` and list rows, the latest day before the evening."""
    summary = [SUMMARY] if summary is None else summary
    first = ({"title": "114年01月03日 當日沖銷交易統計資訊", "fields": SUMMARY_FIELDS, "data": summary}
             if summary else {})
    second = ({"title": "114年01月03日 當日沖銷交易標的及成交量值", "fields": TARGET_FIELDS, "data": TARGETS}
              if targets is None else {"title": "115年10月22日 當日沖銷交易標的", "fields": LIST_FIELDS, "data": targets})
    return {"stat": "OK", "date": date, "selectType": "All", "tables": [first, second]}


def _client(payload):
    return OfflineClient({"/dayTrading/TWTB4U": payload})


def test_published_day_becomes_typed_report():
    report = day_trading(_client(reply()), "20250103")
    assert (report.date, report.published) == ("20250103", True)
    s = report.summary
    assert (s.volume, s.volume_pct, s.buy_value, s.buy_pct, s.sell_value, s.sell_pct) == (
        1336093000, Decimal("21.55"), 126279376690, Decimal("37.46"), 126483285690, Decimal("37.52"))
    etf, suspended = report.targets
    assert (etf.code, etf.name, etf.sell_first_suspended, etf.volume, etf.buy_value, etf.sell_value) == (
        "0050", "元大台灣50", False, 269000, 52719950, 52751400)
    assert suspended.sell_first_suspended


def test_list_before_the_evening_publication():
    report = day_trading(_client(reply(summary=[], targets=LIST, date="20261022")))
    assert (report.date, report.summary, report.published) == ("20261022", None, False)
    assert [(t.code, t.sell_first_suspended, t.volume) for t in report.targets] == [("00400A", False, None), ("2330", True, None)]


def test_latest_day_omits_date_and_old_dates_have_none():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return reply()

    day_trading(_client(route))
    assert seen == [{"selectType": "All", "response": "json"}]
    assert day_trading(_client({"stat": "查詢日期小於103年1月6日，請重新查詢!"}), "20100104") is None
    assert day_trading(_client({"stat": "OK", "tables": [{"data": []}, {"data": []}]}), "20260801") is None


def test_changed_fields_are_an_error():
    renamed = reply()
    renamed["tables"][1]["fields"] = TARGET_FIELDS[:3] + ["當沖成交股數"] + TARGET_FIELDS[4:]
    with pytest.raises(UpstreamFormatError, match="當日沖銷交易成交股數"):
        day_trading(_client(renamed), "20250103")
    no_code = reply()
    no_code["tables"][1]["fields"] = ["代號"] + TARGET_FIELDS[1:]
    with pytest.raises(UpstreamFormatError, match="找不到當沖標的表"):
        day_trading(_client(no_code), "20250103")
    with pytest.raises(UpstreamFormatError, match="5 欄"):
        day_trading(_client(reply(summary=[SUMMARY[:5]])), "20250103")


def _tool(payload):
    return register_module_tools(exright_day_trading_indices, _client(payload))["get_daily_day_trading_targets"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())("20250103")
    assert text.startswith("全市場當沖: 成交股數 1,336,093,000（占 21.55%）| 買進金額 126,279,376,690（占 37.46%）| "
                           "賣出金額 126,483,285,690（占 37.52%）\n\n")
    assert "0050 元大台灣50 | 當沖股數:269,000 | 買進:52,719,950 | 賣出:52,751,400\n" in text
    assert "00400A 主動國泰動能高息（暫停先賣後買） | 當沖股數:1,000" in text
    assert "尚未公布" not in text


def test_tool_before_the_evening_publication_lists_targets_only():
    text = _tool(reply(summary=[], targets=LIST, date="20261022"))()
    assert "20261022 上市個股當日沖銷交易" in text and "當日當沖量值尚未公布" in text
    assert "00400A 主動國泰動能高息\n" in text and "2330 台積電（暫停先賣後買）\n" in text


def test_tool_filters_and_reports_no_data():
    fn = _tool(reply())
    assert "共有 1 筆" in fn("20250103", stock_no="0050") and "00400A" not in fn("20250103", name="台灣50")
    # 已公布的日子篩不到股票時，不再誤稱「量值尚未公布」
    assert "尚未公布" not in fn("20250103", stock_no="9999")
    assert "請確認該日期為交易日" in _tool({"stat": "OK", "tables": [{"data": []}, {"data": []}]})("20260801")
