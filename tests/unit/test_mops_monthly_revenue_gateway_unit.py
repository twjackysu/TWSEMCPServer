"""sources/mops/monthly_revenue.py 的單元測試（不打網路）。工具的區間、月增率與查無訊息見 test_mops_unit.py。

回應取自公開資訊觀測站真實回應（2330，民國 115 年 9 月；民國 98 年 12 月只有 yymm）；上游真實格式由
tests/contract/test_mops_api.py::TestMonthlyRevenueGateway 驗證。
"""

import pytest

from sources.mops.monthly_revenue import monthly_revenue
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.mops import monthly_revenue as monthly_revenue_tool
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

TITLES = [{"sub": [], "main": "項目"}, {"sub": [], "main": "營業收入淨額"}]
DATA = [["本月", "511,857,399"], ["去年同期", "330,980,920"], ["增減金額", "180,876,479"], ["增減百分比", "54.65"],
        ["本年累計", "3,898,726,974"], ["去年累計", "2,762,963,851"], ["增減金額", "1,135,763,123"],
        ["增減百分比", "41.11"], ["備註/營收變化原因說明", "因先進製程產品需求增加所致。"]]


def ok(result):
    return {"code": 200, "message": "查詢成功", "result": result}


def reply(data=None, titles=None, yymm="11509"):
    return ok({"companyAbbreviation": "台積電", "yymm": yymm, "marketKindName": "上市", "note": "",
               "titles": titles or TITLES, "data": DATA if data is None else data})


def test_items_period_and_current_month():
    report = monthly_revenue(OfflineClient({"/mops/api/t05st10_ifrs": reply()}), "2330")
    assert (report.name, report.period, report.current) == ("台積電", (2026, 9), 511857399)
    assert [(i.label, i.value) for i in report.items][-2:] == [("增減百分比", "41.11"),
                                                               ("備註/營收變化原因說明", "因先進製程產品需求增加所致。")]


def test_request_body_and_months_before_ifrs():
    seen = []

    def route(_params, body):
        seen.append(dict(body))
        return ok({"marketKindName": "上市", "yymm": "09812"})

    report = monthly_revenue(OfflineClient({"/mops/api/t05st10_ifrs": route}), "2330", 2009, 12)
    assert seen == [{"companyId": "2330", "dataType": "2", "year": "98", "month": "12", "subsidiaryCompanyId": ""}]
    assert (report.period, report.items, report.current) == ((2009, 12), [], None)
    monthly_revenue(OfflineClient({"/mops/api/t05st10_ifrs": route}), "2330", 2026, 8)
    assert (seen[-1]["year"], seen[-1]["month"]) == ("115", "8")  # month is not zero-padded
    assert monthly_revenue(OfflineClient({"/mops/api/t05st10_ifrs": {"code": 406, "message": "查無", "result": None}}),
                           "9999") is None


def test_changed_titles_are_an_error():
    with pytest.raises(UpstreamFormatError, match="營業收入淨額"):
        monthly_revenue(OfflineClient({"/mops/api/t05st10_ifrs": reply(titles=TITLES[:1] + [{"main": "營收"}])}), "2330")
    with pytest.raises(UpstreamFormatError, match="對不上"):
        monthly_revenue(OfflineClient({"/mops/api/t05st10_ifrs": reply([["本月"]])}), "2330")


def test_tool_prints_the_items_as_before():
    fn = register_module_tools(monthly_revenue_tool, OfflineClient({"/mops/api/t05st10_ifrs": reply()}))[
        "get_company_monthly_revenue"]
    text = fn("2330", "202609")
    assert ("2026-09 | 本月:511,857,399 | 月增率:0.00 | 去年同期:330,980,920 | 增減金額:180,876,479 | 增減百分比:54.65 | "
            "本年累計:3,898,726,974 | 去年累計:2,762,963,851 | 增減金額:1,135,763,123 | 增減百分比:41.11 | "
            "備註/營收變化原因說明:因先進製程產品需求增加所致。") in text
