"""sources/tpex/insti_summary.py 與 get_otc_institutional_summary 的單元測試（不打網路）。

上游真實格式由 tests/contract/test_otc_history_api.py::TestOTCInstitutionalSummaryGateway 驗證。
"""

import pytest

from sources.tpex.insti_summary import otc_institutional_amounts
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.otc import institutional_summary
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

FIELDS = ["單位名稱", "買進金額(元)", "賣出金額(元)", "買賣超(元)"]
ROWS = [
    ["外資及陸資合計", "20,309,758,499", "17,880,081,999", "2,429,676,500"],
    ["　外資及陸資(不含自營商)", "20,309,758,499", "17,880,081,999", "2,429,676,500"],
    ["　外資自營商", "0", "0", "0"],
    ["投信", "2,933,102,722", "2,057,675,469", "875,427,253"],
    ["自營商合計", "1,402,823,597", "1,402,907,710", "-84,113"],
    ["三大法人合計*", "24,645,684,818", "21,340,665,178", "3,305,019,640"],
]
SUBTITLE = "114年01月03日上櫃股票三大法人日彙總交易資訊"


def reply(rows=None, fields=None, **table):
    return {"date": "20250103", "stat": "ok",
            "tables": [{"subtitle": SUBTITLE, "fields": fields or FIELDS, "data": ROWS if rows is None else rows, **table}]}


def _summary(payload, **kwargs):
    return otc_institutional_amounts(OfflineClient({"/insti/summary": payload}), **kwargs)


def test_rows_become_amounts_with_indented_names_stripped():
    s = _summary(reply())
    assert (s.date, s.subtitle) == ("20250103", SUBTITLE)
    assert [a.name for a in s.amounts][:3] == ["外資及陸資合計", "外資及陸資(不含自營商)", "外資自營商"]
    dealer = s.amounts[4]
    assert (dealer.buy, dealer.sell, dealer.net) == (1402823597, 1402907710, -84113)


def test_an_empty_row_is_skipped_not_a_failure():
    # 2018-01-02: four rows, then []
    rows = [["投信", "189,257,359", "517,516,125", "-328,258,766"], []]
    assert [a.name for a in _summary(reply(rows)).amounts] == ["投信"]


def test_renamed_column_or_row_width_change_is_an_error():
    with pytest.raises(UpstreamFormatError, match="買賣超"):
        _summary(reply(fields=FIELDS[:3] + ["淨額(元)"]))
    with pytest.raises(UpstreamFormatError, match="4 個"):
        _summary(reply([ROWS[0][:3]]))
    with pytest.raises(UpstreamFormatError, match="tables"):
        _summary({"stat": "ok"})


def test_a_period_without_data_has_no_amounts():
    assert _summary(reply([], subtitle="")).amounts == []


def test_request_parameters():
    seen = {}

    def route(params, _body):
        seen.update(params)
        return reply()

    otc_institutional_amounts(OfflineClient({"/insti/summary": route}), "Weekly", "0", "20261014")
    assert seen == {"type": "Weekly", "prod": "0", "date": "2026/10/14", "response": "json"}
    seen.clear()
    otc_institutional_amounts(OfflineClient({"/insti/summary": route}))
    assert seen == {"type": "Daily", "prod": "1", "response": "json"}


def _tool(payload):
    return register_module_tools(institutional_summary, OfflineClient({"/insti/summary": payload}))["get_otc_institutional_summary"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(reply())("20250103")
    assert text.startswith(f"【{SUBTITLE}】（單位：億元）\n")
    assert "外資及陸資合計：買進 203.10 億 | 賣出 178.80 億 | 買賣超 24.30 億（2,429,676,500 元）" in text
    assert "外資自營商：買進 0.00 億 | 賣出 0.00 億 | 買賣超 0.00 億（0 元）" in text
    assert "自營商合計：買進 14.03 億 | 賣出 14.03 億 | 買賣超 -0.00 億（-84,113 元）" in text


def test_tool_answers_a_day_with_an_empty_row():
    rows = [["投信", "189,257,359", "517,516,125", "-328,258,766"], []]
    assert "投信：買進 1.89 億 | 賣出 5.18 億 | 買賣超 -3.28 億（-328,258,766 元）" in _tool(reply(rows))("20180102")
