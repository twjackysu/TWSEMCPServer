"""sources/twse/mi_qfiis.py 與 get_foreign_holdings 的單元測試（不打網路）。

欄位與數字取自證交所真實回應（2005-01-03、2018-01-02、2025-01-03）；上游真實格式由
tests/contract/test_history_tier1_api.py::TestForeignHoldingsGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.twse.mi_qfiis import foreign_holdings
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.history import foreign_holdings_history
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["證券代號", "證券名稱", "國際證券編碼", "發行股數", "外資及陸資尚可投資股數", "全體外資及陸資持有股數",
          "外資及陸資尚可投資比率", "全體外資及陸資持股比率", "外資及陸資共用法令投資上限比率", "陸資法令投資上限比率",
          "與前日異動原因(註)", "最近一次上市公司申報外資及陸資持股異動日期"]
# The two ratios are JSON numbers.
ROWS = [["0050", "元大台灣50", "TW0000050004", "2,219,000,000", "2,109,833,508", "109,166,492", 95.08, 4.91, "100.00",
         "100.00", "", "113/07/01"],
        ["0051", "元大中型100", "TW0000051002", "495,500,000", "433,061,859", "62,438,141", 87.39, 12.6, "100.00",
         "100.00", "", 0]]
# Until 2009-04-30: 外資 names, no 陸資法令投資上限比率.
OLD_FIELDS = ["證券代號", "證券名稱", "國際證券編碼", "發行股數", "外資尚可投資股數", "全體外資持有股數", "外資尚可投資比率",
              "全體外資持股比率", "法令投資上限比率", "與前日異動原因(註)", "最近一次上市公司申報外資持股異動日期"]
OLD_ROWS = [["0001", "鴻運", "TW0000001007", "500,000,000", "414,951,000", "85,049,000", 82.99, 17.0, "100.00", "", 0]]


def reply(rows=None, fields=None, date="20250103"):
    return {"stat": "OK", "date": date, "title": "114年01月03日 外資及陸資投資持股統計", "selectType": "ALLBUT0999",
            "fields": fields or FIELDS, "data": ROWS if rows is None else rows}


def _client(payload):
    return OfflineClient({"/fund/MI_QFIIS": payload})


def test_rows_become_typed_holdings():
    day = foreign_holdings(_client(reply()), "20250103")
    etf, mid = day.holdings
    assert day.date == "20250103"
    assert (etf.code, etf.name, etf.issued_shares, etf.available_shares, etf.held_shares) == (
        "0050", "元大台灣50", 2219000000, 2109833508, 109166492)
    assert (etf.available_pct, etf.held_pct, etf.limit_pct) == (Decimal("95.08"), Decimal("4.91"), Decimal("100.00"))
    assert mid.held_pct == Decimal("12.6")


def test_names_before_mainland_investors_were_admitted():
    (h,) = foreign_holdings(_client(reply(OLD_ROWS, OLD_FIELDS, date="20050103")), "20050103").holdings
    assert (h.code, h.held_shares, h.available_pct, h.held_pct, h.limit_pct) == (
        "0001", 85049000, Decimal("82.99"), Decimal("17.0"), Decimal("100.00"))


def test_latest_day_empty_day_and_refusal():
    seen = []

    def route(params, _body):
        seen.append(dict(params))
        return reply()

    foreign_holdings(_client(route))
    assert seen == [{"response": "json", "selectType": "ALLBUT0999"}]
    assert foreign_holdings(_client(reply([], date="20260927")), "20260927").holdings == []
    assert foreign_holdings(_client({"stat": "很抱歉，沒有符合條件的資料!"}), "20260927") is None


def test_changed_fields_are_an_error():
    with pytest.raises(UpstreamFormatError, match="全體外資及陸資持股比率"):
        foreign_holdings(_client(reply(fields=FIELDS[:7] + ["外資持股比率"] + FIELDS[8:])), "20250103")
    with pytest.raises(UpstreamFormatError, match="11 欄"):
        foreign_holdings(_client(reply([ROWS[0][:11]])), "20250103")


def _tool(payload):
    return register_module_tools(foreign_holdings_history, _client(payload))["get_foreign_holdings"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    assert ("0050 元大台灣50 | 外資持股比率:4.91% | 尚可投資比率:95.08% | 投資上限:100.00% | 持有股數:109,166,492 | "
            "發行股數:2,219,000,000\n") in _tool(reply())("20250103")
    assert ("0001 鴻運 | 外資持股比率:17.0% | 尚可投資比率:82.99% | 投資上限:100.00% | 持有股數:85,049,000 | "
            "發行股數:500,000,000\n") in _tool(reply(OLD_ROWS, OLD_FIELDS, date="20050103"))("20050103")


def test_tool_sorts_filters_and_reports_no_data():
    fn = _tool(reply())
    ranked = fn("20250103", sort_by="ratio")
    assert "依持股比率由高到低" in ranked and ranked.index("0051") < ranked.index("0050")
    assert "共有 1 筆" in fn("20250103", stock_no="0051") and "查無股票代號 9999" in fn("20250103", stock_no="9999")
    assert "查無名稱包含「台積」" in fn("20250103", name="台積")
    assert _tool(reply([], date="20260927"))("20260927") == "查無 20260927 的外資及陸資持股資料"
    assert "請確認該日期為交易日" in _tool({"stat": "很抱歉，沒有符合條件的資料!"})("20260927")
