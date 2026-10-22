"""sources/mops/financial_statements.py 的單元測試（不打網路）。工具的年季參數與查無訊息見 test_mops_unit.py。

titles 與資料列取自公開資訊觀測站真實回應（台積電、國泰金 民國 114 年第 2 季綜合損益表，台積電 114 年第 4 季現金流量表）；
上游真實格式由 tests/contract/test_mops_api.py::TestFinancialStatementsGateway 驗證。
"""

from decimal import Decimal

import pytest

from sources.mops.financial_statements import financial_statement
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.mops import financial_statements as statements_tool
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline


def _period(main, measures=("金額", "%")):
    return {"sub": [{"sub": [], "main": m} for m in measures], "main": main}


INCOME_TITLES = [{"sub": [], "main": "會計項目"}, _period("114年第2季"), _period("113年第2季"),
                 _period("114年01月01日至114年06月30日"), _period("113年01月01日至113年06月30日")]
INCOME_ROWS = [
    ["營業收入合計", "933,791,869", "100.00", "673,510,177", "100.00", "1,773,045,533", "100.00", "1,266,154,378", "100.00"],
    ["營業費用", "", "", "", "", "", "", "", ""],
    ["　　推銷費用", "4,273,247", "0.46", "2,947,324", "0.44", "8,028,062", "0.45", "6,058,583", "0.48"],
    ["　其他收益及費損淨額", "562,739", "0.06", "-1,273,626", "-0.19", "-565,473", "-0.03", "-1,403,308", "-0.11"],
    ["　基本每股盈餘", "15.36", "", "9.56", "", "29.31", "", "18.25", ""],
]
# 國泰金：百分比沒有千分位
EXCHANGE_ROW = ["　　兌換損益", "-334,983,959", "-1362.67", "49,312,157", "68.95", "-290,138,707", "-221.74",
                "180,164,254", "95.79"]
CASHFLOW_TITLES = [{"sub": [], "main": "會計項目"}, _period("114年度", ("金額",)), _period("113年度", ("金額",))]
CASHFLOW_ROWS = [["營業活動之現金流量－間接法", "", ""],
                 ["　繼續營業單位稅前淨利（淨損）", "2,041,662,840", "1,405,838,635"],
                 ["　　　利息收入", "-105,739,081", "-87,213,399"]]


def reply(rows=None, titles=None, name="台積電"):
    return {"code": 200, "message": "查詢成功", "result": {
        "companyAbbreviation": name, "reportType": "合併", "year": "114", "season": "2", "fiscalYear": " ",
        "subsidiary": [], "urlList": [], "titles": INCOME_TITLES if titles is None else titles,
        "reportList": INCOME_ROWS if rows is None else rows}}


def _client(body, api="t164sb04"):
    return OfflineClient({f"/mops/api/{api}": body})


def test_columns_lines_and_headings():
    s = financial_statement(_client(reply()), "income", "2330", 114, 2)
    assert (s.name, s.report_type) == ("台積電", "合併")
    assert s.columns[:3] == ("114年第2季 金額", "114年第2季 %", "113年第2季 金額")
    assert len(s.columns) == 8
    revenue, expenses, selling, other, eps = s.lines
    assert revenue.values[:2] == (Decimal("933791869"), Decimal("100.00")) and revenue.level == 0
    assert expenses.is_heading and expenses.item == "營業費用"
    assert (selling.item, selling.level, selling.is_heading) == ("推銷費用", 2, False)
    assert other.values[2:4] == (Decimal("-1273626"), Decimal("-0.19"))
    assert eps.values[:2] == (Decimal("15.36"), None)


def test_cash_flow_has_amounts_only():
    s = financial_statement(_client(reply(CASHFLOW_ROWS, CASHFLOW_TITLES), "t164sb05"), "cashflow", "2330", 114, 4)
    assert s.columns == ("114年度 金額", "113年度 金額")
    assert s.lines[0].is_heading and s.lines[2].values == (Decimal("-105739081"), Decimal("-87213399"))


def test_request_bodies_and_endpoints():
    seen = []

    def route(api):
        def answer(_params, body):
            seen.append((api, dict(body)))
            return reply()
        return answer

    client = OfflineClient({f"/mops/api/{a}": route(a) for a in ("t164sb03", "t164sb04", "t164sb05")})
    financial_statement(client, "income", "2330")
    financial_statement(client, "balance", "2330", 114, 2)
    financial_statement(client, "cashflow", "2330", 102, 4)
    assert seen == [
        ("t164sb04", {"companyId": "2330", "dataType": "1", "year": "", "season": "", "subsidiaryCompanyId": ""}),
        ("t164sb03", {"companyId": "2330", "dataType": "2", "year": "114", "season": "2", "subsidiaryCompanyId": ""}),
        ("t164sb05", {"companyId": "2330", "dataType": "2", "year": "102", "season": "4", "subsidiaryCompanyId": ""}),
    ]


def test_no_data_and_changed_format():
    no_data = {"code": 406, "message": "查無相符資料", "result": None}
    assert financial_statement(_client(no_data), "income", "2330", 119, 1) is None
    assert financial_statement(_client(reply(rows=[])), "income", "2330") is None
    renamed = [{"sub": [], "main": "項目"}] + INCOME_TITLES[1:]
    with pytest.raises(UpstreamFormatError, match="會計項目"):
        financial_statement(_client(reply(titles=renamed)), "income", "2330")
    with pytest.raises(UpstreamFormatError, match="titles 對不上"):
        financial_statement(_client(reply([INCOME_ROWS[0][:5]])), "income", "2330")
    with pytest.raises(UpstreamFormatError, match="數字格式"):
        financial_statement(_client(reply([["營業收入合計", "N/A"] + INCOME_ROWS[0][2:]])), "income", "2330")


def test_tool_prints_amounts_with_separators_and_percentages_without():
    tools = register_module_tools(statements_tool, _client(reply(INCOME_ROWS + [EXCHANGE_ROW], name="國泰金")))
    text = tools["get_company_income_statement"]("2882", "2025", 2)
    lines = text.splitlines()
    assert lines[0] == "【國泰金(2882) 合併綜合損益表】（單位：新台幣仟元；每股盈餘為元）"
    assert lines[1].startswith("欄位: 114年第2季 金額 | 114年第2季 % | 113年第2季 金額")
    assert "〔營業費用〕" in lines
    assert "推銷費用: 4,273,247 | 0.46 | 2,947,324 | 0.44 | 8,028,062 | 0.45 | 6,058,583 | 0.48" in lines
    assert "基本每股盈餘: 15.36 | - | 9.56 | - | 29.31 | - | 18.25 | -" in lines
    assert ("兌換損益: -334,983,959 | -1362.67 | 49,312,157 | 68.95 | -290,138,707 | -221.74 | 180,164,254 | 95.79"
            in lines)
