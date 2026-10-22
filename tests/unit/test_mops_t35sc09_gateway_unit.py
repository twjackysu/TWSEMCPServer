"""sources/mops/t35sc09.py 與 get_treasury_stock_buybacks 的單元測試（不打網路）。

表頭標記與資料列取自公開資訊觀測站真實回應（99 年上櫃、115 年上市）；上游真實格式由
tests/contract/test_mops_api.py 的 TestTreasuryAndGuaranteesLegacyPages 驗證。
"""

import pytest
from decimal import Decimal
from fastmcp.exceptions import ToolError

from sources.mops.t35sc09 import treasury_buybacks
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.mops import treasury_guarantees
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

TOP = ("<tr class='tblHead'><th nowrap rowspan='2' >序<br>號</th><th nowrap rowspan='2' >公司<br>代號</th>"
       "<th nowrap rowspan='2' >公司<br>名稱</th><th nowrap rowspan='2' >董事會<br>決議日期</th>"
       "<th nowrap rowspan='2' >買回<br>目的</th><th nowrap rowspan='2' >買回股份總金額上限<br><font color='red'>"
       "(依最新財報計算<br>之法定上限)</font></th><th nowrap rowspan='2' >預定買回股數</th>"
       "<th nowrap colspan='2' >買回價格區間</th><th nowrap colspan='2' >預定買回期間</th>"
       "<th nowrap rowspan='2' >是否<br>執行<br>完畢</th><th nowrap rowspan='2' >買回達<br>一定標<br>準資料</th>"
       "<th nowrap rowspan='2' >本次已買回<br>股數<br><font color='red'>(空白為尚<br>在執行中)</font></th>"
       "<th nowrap rowspan='2' >本次執行完畢<br>已註銷或<br>轉讓股數</th><th nowrap rowspan='2' >本次已買回<br>"
       "股數佔預定<br>買回股數比<br>例(%)<br><font color='red'>(空白為尚<br>在執行中)</font></th>"
       "<th nowrap rowspan='2' >本次已買回<br>總金額<br><font color='red'>(空白為尚<br>在執行中)</font></th>"
       "<th nowrap rowspan='2' >本次平均<br>每股買回<br>價格<br><font color='red'>(空白為尚<br>在執行中)</font></th>"
       "<th nowrap rowspan='2' >本次買回股<br>數佔公司已<br>發行股份總<br>數比例(%)<br><font color='red'>(空白為尚<br>"
       "在執行中)</font></th><th nowrap rowspan='2' >本次未執行<br>完畢之原因</th></tr>")
SUB = "<tr class='tblHead'><th nowrap >最低</th><th nowrap >最高</th><th nowrap >起</th><th nowrap >迄</th></tr>"
FINISHED_WITH_REASON = ["1", "1785", "光洋科", "99/02/09", "1", "4,519,546,749", "2,500,000", "52.00", "120.00",
                        "99/02/10", "99/04/09", "Y", "", "661,000", "661,000", "26.44", "47,206,254", "71.42", "0.26",
                        "為兼顧市場機制及全體股東利益，故本次買回庫藏股未能執行完畢。"]
NOTHING_BOUGHT = ["4", "5489", "彩富", "99/02/24", "1", "451,971,547", "3,000,000", "26.00", "55.09", "99/02/25",
                  "99/04/24", "Y", "", "0", "", "0.00", "0", "0.00", "0.00", "價格偏高"]
RUNNING = ["21", "5546", "永固-KY", "115/08/24", "3", "828,309,501", "1,000,000", "12.00", "21.00", "115/08/25",
           "115/10/23", "N"] + [""] * 8


def _row(cells):
    tds = []
    for i, c in enumerate(cells):
        if i == 12:  # 買回達一定標準資料 is a button
            tds.append("<td>\n<input type='button' value='查詢' onclick='ajax1(this.form,\"table01\");'/>\n</td>")
        else:
            tds.append(f"<td align='right'>     {c or '&nbsp;'}</td>")
    return "<tr class= 'even' align='center'>" + "\n".join(tds) + "</tr>"


def page(*rows, top=TOP, sub=SUB):
    """A t35sc09 reply: title table, then the data table — split in two, header repeated and the first table
    left open, the way MOPS does every few hundred rows — then the totals."""
    half = len(rows) // 2 or len(rows)
    body = "".join(f"<table class='hasBorder' width='95%'>{top}{sub}" + "".join(_row(r) for r in part)
                   for part in (rows[:half], rows[half:]) if part)
    return ("<table class='noBorder'><tr><td>上櫃公司買回自己公司股份彙總統計表</td></tr></table>"
            "<table class='noBorder' width='95%'><tr ><td align='left' >日期：099/01/01~099/12/31</td>"
            f"<td align='right' >出表日：115/10/22</td></tr></table>{body}</table>"
            "<table><tr><td>家數合計：3家</td></tr></table>").encode("utf-8")


NO_DATA = "<html><table><tr><td>上市公司買回自己公司股份彙總統計表</td></tr><tr><td>查無所需資料</td></tr></table></html>"


def _client(body):
    return OfflineClient({"/ajax_t35sc09": body})


def test_rows_become_typed_buybacks():
    done, nothing, running = treasury_buybacks(_client(page(FINISHED_WITH_REASON, NOTHING_BOUGHT, RUNNING)),
                                               "otc", "20100101", "20101231")
    assert (done.code, done.name, done.resolution_date, done.purpose, done.completed) == (
        "1785", "光洋科", "99/02/09", "1", "Y")
    assert (done.amount_cap, done.planned_shares, done.price_low, done.price_high) == (
        Decimal("4519546749"), 2500000, Decimal("52.00"), Decimal("120.00"))
    assert (done.period_start, done.period_end, done.bought_shares, done.cancelled_shares) == (
        "99/02/10", "99/04/09", 661000, 661000)
    assert (done.pct_of_planned, done.bought_amount, done.average_price, done.pct_of_issued) == (
        Decimal("26.44"), Decimal("47206254"), Decimal("71.42"), Decimal("0.26"))
    assert done.unfinished_reason.startswith("為兼顧市場機制")
    assert (nothing.bought_shares, nothing.cancelled_shares, nothing.unfinished_reason) == (0, None, "價格偏高")
    assert (running.completed, running.bought_shares, running.average_price, running.unfinished_reason) == (
        "N", None, None, "")


def test_form_fields():
    forms = []

    def route(_params, form):
        forms.append(dict(form))
        return NO_DATA.encode("utf-8")

    assert treasury_buybacks(_client(route), "sii", "20260901", "20260930") is None
    assert {k: forms[0][k] for k in ("TYPEK", "d1", "d2", "RD")} == {
        "TYPEK": "sii", "d1": "1150901", "d2": "1150930", "RD": "1"}


def test_changed_header_or_page_is_an_error():
    with pytest.raises(UpstreamFormatError, match="本次已買回總金額"):
        treasury_buybacks(_client(page(RUNNING, top=TOP.replace("總金額", "金額"))), "sii", "20260901", "20260930")
    with pytest.raises(UpstreamFormatError, match="第二列表頭"):
        treasury_buybacks(_client(page(RUNNING, sub=SUB.replace("最低", "低"))), "sii", "20260901", "20260930")
    with pytest.raises(UpstreamFormatError, match="19 格"):
        treasury_buybacks(_client(page(RUNNING[:19])), "sii", "20260901", "20260930")
    with pytest.raises(UpstreamFormatError, match="非預期頁面"):
        treasury_buybacks(_client(b"<html>FOR SECURITY REASONS</html>"), "sii", "20260901", "20260930")


def _tool(body):
    return register_module_tools(treasury_guarantees, _client(body))["get_treasury_stock_buybacks"]


def test_tool_prints_the_same_lines_as_before_the_gateway():
    text = _tool(page(FINISHED_WITH_REASON, NOTHING_BOUGHT, RUNNING))("20100101", "20101231", market="otc")
    assert ("1785 光洋科 | 決議:99/02/09 | 目的:轉讓股份予員工 | 上限:4,519,546,749元 | 預定:2,500,000股 @52.00～120.00 | "
            "期間:99/02/10～99/04/09 | 是否執行完畢:Y | 已買回:661,000股（佔預定 26.44%，佔已發行 0.26%） 金額:47,206,254 "
            "均價:71.42 | 未完畢原因:為兼顧市場機制及全體股東利益，故本次買回庫藏股未能執行完畢。\n") in text
    assert ("5489 彩富 | 決議:99/02/24 | 目的:轉讓股份予員工 | 上限:451,971,547元 | 預定:3,000,000股 @26.00～55.09 | "
            "期間:99/02/25～99/04/24 | 是否執行完畢:Y | 已買回:0股（佔預定 0.00%，佔已發行 0.00%） 金額:0 均價:0.00 | "
            "未完畢原因:價格偏高\n") in text
    assert ("5546 永固-KY | 決議:115/08/24 | 目的:維護公司信用及股東權益 | 上限:828,309,501元 | 預定:1,000,000股 "
            "@12.00～21.00 | 期間:115/08/25～115/10/23 | 是否執行完畢:N\n") in text


def test_tool_filters_by_code_and_reports_no_data():
    fn = _tool(page(FINISHED_WITH_REASON, NOTHING_BOUGHT, RUNNING))
    text = fn("20100101", "20101231", code="5489")
    assert "共有 1 筆" in text and "彩富" in text and "光洋科" not in text
    assert "查無" in _tool(NO_DATA.encode("utf-8"))("20261020", "20261021")
    with pytest.raises(ToolError, match="^查詢失敗.*非預期頁面"):
        _tool(b"<html>FOR SECURITY REASONS</html>")("20261020", "20261021")
