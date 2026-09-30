"""utils/mops.py 與 tools/mops/ 的單元測試（不打網路）。

MOPS 的欄位結構由 tests/e2e/test_mops_api.py 驗證；這裡只測我們自己的邏輯：
回應碼判讀、表頭攤平、HTML 表格解析、月份/年度參數處理、依欄名查找欄位。
"""

from datetime import date

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.mops import dividend, financial_statements, investor_conference, monthly_revenue
from tools.mops.monthly_revenue import parse_month_range
from utils.mops import MopsQueryError, flatten_titles, leaf_titles, mops_post, parse_html_table, to_roc_year

pytestmark = pytest.mark.offline

NESTED_TITLES = [
    {"main": "會計項目", "sub": []},
    {"main": "114年第2季", "sub": [{"main": "金額", "sub": []}, {"main": "%", "sub": []}]},
]


def _ok(result):
    return {"code": 200, "message": "查詢成功", "result": result}


# ---------- utils.mops ----------

def test_flatten_titles_prefixes_group_names():
    assert flatten_titles(NESTED_TITLES) == ["會計項目", "114年第2季 金額", "114年第2季 %"]


def test_leaf_titles_drops_group_names():
    assert leaf_titles(NESTED_TITLES) == ["會計項目", "金額", "%"]


@pytest.mark.parametrize("year,expected", [("2025", 114), ("114", 114), (" 2026 ", 115), ("99", 99)])
def test_to_roc_year_accepts_both_calendars(year, expected):
    assert to_roc_year(year) == expected


def test_mops_post_returns_result_on_200():
    client = OfflineClient({"/mops/api/t164sb04": _ok({"x": 1})})
    assert mops_post(client, "t164sb04", {}) == {"x": 1}


def test_mops_post_treats_406_as_no_data():
    client = OfflineClient({"/mops/api/t164sb04": {"code": 406, "message": "查無相符資料", "result": None}})
    assert mops_post(client, "t164sb04", {}) is None


def test_mops_post_raises_on_other_codes():
    """參數錯誤不能被當成「查無資料」，否則使用者會以為該公司真的沒有財報."""
    client = OfflineClient({"/mops/api/t164sb04": {"code": 500, "message": "公司代號格式錯誤", "result": None}})
    with pytest.raises(MopsQueryError, match="公司代號格式錯誤"):
        mops_post(client, "t164sb04", {})


def test_parse_html_table_targets_table_by_id_and_cleans_text():
    html = """
    <table id='other'><tr><td>ignore</td></tr></table>
    <table id='myTable'>
      <tr><th>代號</th><th>內容</th></tr>
      <tr><td>2330</td><td>第一行<br>第二行 &amp; 更多</td></tr>
      <tr><td>2317</td><td><table><tr><td>巢狀</td></tr></table></td></tr>
    </table>
    <table id='after'><tr><td>ignore</td></tr></table>
    """
    rows = parse_html_table(html, "myTable")
    assert rows[0] == ["代號", "內容"]
    assert rows[1] == ["2330", "第一行 第二行 & 更多"]
    assert rows[2] == ["2317", "巢狀"]  # 巢狀表格併入外層儲存格文字，不另起一列
    assert len(rows) == 3


# ---------- financial statements ----------

def test_statement_rows_render_against_their_own_headers():
    result = {
        "companyAbbreviation": "台積電", "reportType": "合併",
        "titles": NESTED_TITLES,
        "reportList": [["營業費用", "", ""], ["　　推銷費用", "4,273,247", "0.46"]],
    }
    text = financial_statements.format_statement(result, "2330", "綜合損益表")
    assert "欄位: 114年第2季 金額 | 114年第2季 %" in text
    assert "〔營業費用〕" in text  # 全空列是段落標題
    assert "推銷費用: 4,273,247 | 0.46" in text


def test_statement_tool_sends_roc_year_and_rejects_bad_season():
    seen = {}

    def route(_params, body):
        seen.update(body)
        return _ok({"titles": NESTED_TITLES, "reportList": [["營業收入合計", "1", "100.00"]]})

    tools = register_module_tools(financial_statements, OfflineClient({"/mops/api/t164sb05": route}))
    fn = tools["get_company_cash_flow_statement"]
    assert "營業收入合計" in fn("2330", "2025", 4)
    assert (seen["year"], seen["season"], seen["dataType"]) == ("114", "4", "2")
    assert "請同時指定 year 與 season" in fn("2330", "2025", 5)
    assert "請同時指定 year 與 season" in fn("2330", "2025")


def test_statement_tool_defaults_to_latest_quarter():
    """不帶年季 → dataType=1 並帶空的 year/season（少了這兩欄 MOPS 會回參數異常）."""
    seen = {}

    def route(_params, body):
        seen.update(body)
        return _ok({"titles": NESTED_TITLES, "reportList": [["營業收入合計", "1", "100.00"]]})

    tools = register_module_tools(financial_statements, OfflineClient({"/mops/api/t164sb04": route}))
    assert "營業收入合計" in tools["get_company_income_statement"]("2330")
    assert seen == {"companyId": "2330", "dataType": "1", "year": "", "season": "", "subsidiaryCompanyId": ""}


def test_statement_tool_reports_unpublished_quarter():
    client = OfflineClient({"/mops/api/t164sb04": {"code": 406, "message": "查無相符資料", "result": None}})
    tools = register_module_tools(financial_statements, client)
    assert "查無 2330 在116 年第 1 季" in tools["get_company_income_statement"]("2330", "2027", 1)


# ---------- monthly revenue ----------

def test_month_range_crosses_year_boundary():
    months, error = parse_month_range("202511", "202602")
    assert error is None
    assert months == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]


@pytest.mark.parametrize("start,end,message", [
    ("2026-01", "202602", "格式錯誤"),
    ("202613", "202613", "格式錯誤"),
    ("202603", "202601", "不可晚於"),
    ("202501", "202601", "最多 12 個月"),
])
def test_month_range_rejections(start, end, message):
    months, error = parse_month_range(start, end)
    assert months is None and message in error


REVENUE_BY_MONTH = {"7": "80", "8": "100"}


def _revenue_route(seen=None):
    def route(_params, body):
        if seen is not None:
            seen.append(dict(body))
        month = body["month"] or "8"  # dataType=1（最新）時 month 為空，回 8 月
        if month not in REVENUE_BY_MONTH:
            return {"code": 406, "message": "查無相符資料", "result": None}
        return _ok({"companyAbbreviation": "台積電", "yymm": f"1150{month}",
                    "data": [["本月", REVENUE_BY_MONTH[month]], ["增減百分比", "5.0"]]})
    return route


def test_revenue_range_adds_mom_and_marks_unpublished_months():
    tools = register_module_tools(monthly_revenue, OfflineClient({"/mops/api/t05st10_ifrs": _revenue_route()}))
    text = tools["get_company_monthly_revenue"]("2330", "202608", "202609")
    assert "2026-08 | 本月:100 | 月增率:25.00 | 增減百分比:5.0" in text  # 多抓的 7 月只用來算月增率
    assert "2026-07" not in text
    assert "2026-09: 尚未公告或查無資料" in text
    assert text.startswith("【台積電(2330)")


def test_revenue_defaults_to_latest_month_with_prior_month():
    seen = []
    tools = register_module_tools(monthly_revenue, OfflineClient({"/mops/api/t05st10_ifrs": _revenue_route(seen)}))
    text = tools["get_company_monthly_revenue"]("2330")
    assert seen[0] == {"companyId": "2330", "dataType": "1", "year": "", "month": "", "subsidiaryCompanyId": ""}
    assert (seen[1]["year"], seen[1]["month"]) == ("115", "7")
    assert "2026-07 | 本月:80" in text and "2026-08 | 本月:100 | 月增率:25.00" in text


# ---------- dividend history ----------

def _dividend_section(titles, row):
    return {"titles": [{"main": t, "sub": []} for t in titles], "data": [row]}


def test_dividend_columns_are_found_by_name_not_position():
    titles = list(reversed(dividend.KEY_COLUMNS))
    row = [f"v:{t}" for t in titles]
    lines = dividend.format_dividend_rows(_dividend_section(titles, row), "普通股")
    for col in dividend.KEY_COLUMNS:
        assert f"{col}:v:{col}" in lines[1]


def test_dividend_missing_column_shows_na_and_html_is_stripped():
    titles = ["決議（擬議）進度"]
    lines = dividend.format_dividend_rows(_dividend_section(titles, ["<b>董事會決議</b>"]), "普通股")
    assert "決議（擬議）進度:董事會決議" in lines[1]
    assert "股東會日期:N/A" in lines[1]


def test_dividend_tool_validates_arguments_and_maps_year_type():
    seen = {}

    def route(_params, body):
        seen.update(body)
        titles = dividend.KEY_COLUMNS
        return _ok({"companyAbbreviation": "台積電",
                    "commonStock": _dividend_section(titles, ["x"] * len(titles)),
                    "specialStock": {"titles": [], "data": []}})

    tools = register_module_tools(dividend, OfflineClient({"/mops/api/t05st09_2": route}))
    fn = tools["get_company_dividend"]
    assert "依董事會決議年度" in fn("2330", "2023", "2025", year_type="board")
    assert (seen["firstYear"], seen["lastYear"], seen["queryType"]) == ("112", "114", "1")
    assert "year_type 只能是" in fn("2330", "2023", year_type="x")
    fn("2330")
    this_year = date.today().year - 1911
    assert (seen["firstYear"], seen["lastYear"]) == (str(this_year - 1), str(this_year))
    assert "不可晚於" in fn("2330", "2025", "2023")
    assert "最多 10 年" in fn("2330", "2010", "2025")


# ---------- investor conferences ----------

CONF_HTML = """<table id='myTable'>
<tr><th>公司代號</th><th>公司名稱</th></tr><tr><th>中文檔案</th><th>英文檔案</th></tr>
<tr>{late}</tr><tr>{early}</tr></table>"""


def _conf_row(code, day):
    cells = [code, "名稱", day, "14:00", "地點", "摘要", "zh.pdf", "en.pdf", "https://x", "", "無。", ""]
    return "".join(f"<td>{c}</td>" for c in cells)


def test_conference_month_is_zero_padded_and_rows_sorted_by_date():
    seen = {}

    def route(_params, body):
        seen.update(body)
        html = CONF_HTML.format(late=_conf_row("1101", "115/09/30"), early=_conf_row("2330", "115/09/01"))
        return html.encode("utf-8")

    tools = register_module_tools(investor_conference, OfflineClient({"/mops/web/ajax_t100sb02_1": route}))
    text = tools["get_investor_conferences"]("2026", "9")
    assert seen["month"] == "09" and seen["year"] == "115" and seen["step"] == "1"
    assert text.index("115/09/01") < text.index("115/09/30")


def test_conference_argument_validation():
    tools = register_module_tools(investor_conference, OfflineClient({}))
    fn = tools["get_investor_conferences"]
    assert "market 只能是" in fn("2026", market="nyse")
    assert "month 必須是" in fn("2026", "13")


def test_conference_unexpected_page_is_an_error_not_no_data():
    """防爬封鎖頁或改版頁既無資料表也無「查無資料」，要回報錯誤而非「查無法說會」."""
    pages = {"blocked": b"<html>FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED!</html>",
             "empty": "<html><center>查無資料</center></html>".encode("utf-8")}
    fn = register_module_tools(investor_conference, OfflineClient({"/mops/web/ajax_t100sb02_1": lambda _p, b: pages[b["co_id"]]}))[
        "get_investor_conferences"]
    assert "查詢失敗" in fn("2026", code="blocked")
    assert "查無" in fn("2026", code="empty") and "查詢失敗" not in fn("2026", code="empty")
