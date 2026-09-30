"""公開資訊觀測站 (MOPS) contract tests.

The MOPS JSON API (mops.twse.com.tw/mops/api/*) is the SPA's private backend with no
public docs, so it can change without notice. These tests pin down exactly what
tools/mops/ relies on: request field names, the ``code``/``result`` envelope, the
``titles`` + rows table shape, the column names the dividend tool looks up, and the legacy
法說會 HTML table layout.
"""

from datetime import date

import pytest

from tests.helpers import fetch_or_skip, fetch_bytes_or_skip
from tools.mops.dividend import KEY_COLUMNS
from tools.mops.monthly_revenue import CURRENT_MONTH_LABEL
from tools.mops.investor_conference import NO_DATA_TEXT, ROW_WIDTH, parse_conference_rows
from utils.mops import (
    MOPS_API_BASE,
    MOPS_LEGACY_BASE,
    MOPS_LEGACY_HIDDEN_FIELDS,
    flatten_titles,
    leaf_titles,
    parse_html_table,
)

FIXED_STOCK = "2330"
FIXED_ROC_YEAR = "114"   # 2025，已公告完畢的歷史年度
FIXED_SEASON = "2"


def _mops(api_name: str, body: dict) -> dict:
    resp = fetch_or_skip(f"{MOPS_API_BASE}/{api_name}", json_body=body)
    assert isinstance(resp, dict) and "code" in resp, f"{api_name} 回應外層結構已變更: {resp!r:.300}"
    return resp


def _statement_body(year: str = FIXED_ROC_YEAR) -> dict:
    return {
        "companyId": FIXED_STOCK,
        "dataType": "2",
        "year": year,
        "season": FIXED_SEASON,
        "subsidiaryCompanyId": "",
    }


class TestFinancialStatementsAPI:
    """t164sb03/04/05：tools/mops/financial_statements.py 依 titles 攤平後的欄名
    逐欄輸出 reportList，所以 titles 葉節點數必須等於每列的儲存格數。"""

    @pytest.mark.parametrize("api_name", ["t164sb03", "t164sb04", "t164sb05"])
    def test_report_rows_match_title_columns(self, api_name):
        resp = _mops(api_name, _statement_body())
        assert str(resp["code"]) == "200", f"{api_name} 查詢固定歷史季度失敗: {resp.get('message')}"
        result = resp["result"]
        rows, titles = result.get("reportList"), result.get("titles")
        assert isinstance(rows, list) and rows, f"{api_name} result.reportList 不是非空 list"
        assert isinstance(titles, list) and titles, f"{api_name} result.titles 不是非空 list"
        width = len(flatten_titles(titles))
        bad = [r for r in rows if not isinstance(r, list) or len(r) != width]
        assert not bad, f"{api_name} 列寬與 titles 欄數（{width}）不符，例: {bad[0]!r:.200}"

    def test_latest_mode_needs_empty_year_and_season(self):
        """tool 不帶年季時送 dataType=1 + 空 year/season，MOPS 回最新一季."""
        resp = _mops("t164sb04", {"companyId": FIXED_STOCK, "dataType": "1", "year": "", "season": "",
                                  "subsidiaryCompanyId": ""})
        assert str(resp["code"]) == "200", f"最新一季查詢方式已變更: {resp.get('message')}"
        assert resp["result"].get("reportList"), "最新一季 result.reportList 為空"

    def test_unpublished_quarter_returns_code_406(self):
        """mops_post 把 406 當成「查無資料」（回 None），其他非 200 碼才視為錯誤."""
        future_roc_year = str(date.today().year - 1911 + 2)
        resp = _mops("t164sb04", _statement_body(future_roc_year))
        assert str(resp["code"]) == "406", (
            f"查詢尚未公告的季度不再回 406（實際 {resp['code']} {resp.get('message')}），"
            f"mops_post 的「查無資料」判斷需要更新"
        )


class TestMonthlyRevenueAPI:
    """t05st10_ifrs：tool 將 result.data 當成 [項目, 值] 配對依序輸出。"""

    def test_data_is_label_value_pairs(self):
        resp = _mops("t05st10_ifrs", {
            "companyId": FIXED_STOCK,
            "dataType": "2",
            "year": FIXED_ROC_YEAR,
            "month": "8",
            "subsidiaryCompanyId": "",
        })
        assert str(resp["code"]) == "200", f"查詢固定歷史月份失敗: {resp.get('message')}"
        data = resp["result"].get("data")
        assert isinstance(data, list) and data, "result.data 不是非空 list"
        assert all(isinstance(r, list) and len(r) >= 2 for r in data), f"result.data 不再是 [項目, 值] 配對: {data!r:.300}"
        assert str(data[0][0]).strip() == CURRENT_MONTH_LABEL, (
            f"首列不再是「{CURRENT_MONTH_LABEL}」，月增率計算會失效: {data[0]}"
        )

    def test_latest_mode_returns_yymm(self):
        """tool 不帶月份時送 dataType=1 + 空 year/month，並以 result.yymm 推算前一個月."""
        resp = _mops("t05st10_ifrs", {"companyId": FIXED_STOCK, "dataType": "1", "year": "", "month": "",
                                      "subsidiaryCompanyId": ""})
        assert str(resp["code"]) == "200", f"最新月份查詢方式已變更: {resp.get('message')}"
        yymm = str(resp["result"].get("yymm", ""))
        assert len(yymm) == 5 and yymm.isdigit(), f"result.yymm 格式已變更（預期民國 YYYMM）: {yymm!r}"


class TestDividendHistoryAPI:
    """t05st09_2：tool 以 KEY_COLUMNS 的欄名（非位置）查找欄位。"""

    @pytest.mark.parametrize("query_type", ["1", "2"])
    def test_common_stock_table_has_key_columns(self, query_type):
        resp = _mops("t05st09_2", {
            "companyId": FIXED_STOCK,
            "dataType": "2",
            "firstYear": "113",
            "lastYear": FIXED_ROC_YEAR,
            "queryType": query_type,
        })
        assert str(resp["code"]) == "200", f"queryType={query_type} 查詢失敗: {resp.get('message')}"
        section = resp["result"].get("commonStock") or {}
        names = leaf_titles(section.get("titles", []))
        missing = [c for c in KEY_COLUMNS if c not in names]
        assert not missing, f"commonStock.titles 缺少 tool 使用的欄位: {missing}\n實際: {names}"
        rows = section.get("data")
        assert isinstance(rows, list) and rows, "commonStock.data 不是非空 list"
        assert all(len(r) == len(names) for r in rows), "commonStock.data 列寬與 titles 不符"

    def test_special_stock_section_exists(self):
        resp = _mops("t05st09_2", {
            "companyId": FIXED_STOCK, "dataType": "2", "firstYear": FIXED_ROC_YEAR,
            "lastYear": FIXED_ROC_YEAR, "queryType": "2",
        })
        special = resp["result"].get("specialStock")
        assert isinstance(special, dict) and "titles" in special and "data" in special, (
            f"result.specialStock 結構已變更: {special!r:.200}"
        )


class TestInvestorConferenceLegacyPage:
    """mopsov ajax_t100sb02_1：tool 解析 table#myTable，資料列固定 12 格。"""

    EXPECTED_HEADER = [
        "公司代號", "公司名稱", "召開法人說明會日期", "召開法人說明會時間", "召開法人說明會地點",
        "法人說明會擇要訊息", "法人說明會簡報內容", "公司網站是否提供法人說明會相關資訊",
        "影音連結資訊", "其他應敘明事項", "歷年法人說明會",
    ]

    def _fetch(self, month: str = "", co_id: str = "") -> str:
        body = fetch_bytes_or_skip(
            f"{MOPS_LEGACY_BASE}/ajax_t100sb02_1",
            method="POST",
            data={**MOPS_LEGACY_HIDDEN_FIELDS, "TYPEK": "sii", "year": FIXED_ROC_YEAR, "month": month, "co_id": co_id},
        )
        return body.decode("utf-8", errors="replace")

    def test_table_header_and_row_width(self):
        html = self._fetch(month="07")
        table = parse_html_table(html, "myTable")
        assert table, "找不到 table#myTable，頁面結構已變更"
        assert table[0] == self.EXPECTED_HEADER, f"表頭欄位已變更: {table[0]}"
        rows = parse_conference_rows(html)
        assert rows, f"民國{FIXED_ROC_YEAR}年07月 應有法說會資料（月份需補零）"
        assert all(len(r) == ROW_WIDTH for r in rows)

    def test_company_filter_is_server_side(self):
        rows = parse_conference_rows(self._fetch(co_id=FIXED_STOCK))
        assert rows, f"{FIXED_STOCK} 在民國{FIXED_ROC_YEAR}年應有法說會資料"
        assert {r[0] for r in rows} == {FIXED_STOCK}, "co_id 不再於伺服器端篩選"

    def test_no_data_page_says_so(self):
        """tool 以「查無資料」字樣區分真的沒資料與封鎖／改版頁，這段文字必須還在."""
        html = self._fetch(month="01", co_id="9999")
        assert NO_DATA_TEXT in html, f"查無資料時的頁面文字已變更: {html[:300]!r}"
