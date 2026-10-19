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


class TestMajorNewsAPI:
    """t05st01（公司年度）/ t05st02（某日全市場）：tool 依 row[0..5] 取用，row[5] 是全文連結
    {apiName, parameters}；全文 *_detail 的 row[3],[4],[7],[8],[9] 是發言人、職稱、條款、事實發生日、說明。"""

    def test_company_year_list_and_detail(self):
        resp = _mops("t05st01", {"companyId": FIXED_STOCK, "year": FIXED_ROC_YEAR, "month": "all",
                                 "firstDay": "", "lastDay": ""})
        assert str(resp["code"]) == "200", f"t05st01 查詢失敗: {resp.get('message')}"
        names = leaf_titles(resp["result"].get("titles", []))
        assert names[:5] == ["公司代號", "公司名稱", "發言日期", "發言時間", "主旨"], f"欄位已變更: {names}"
        rows = resp["result"].get("data") or []
        assert rows and isinstance(rows[0][5], dict) and rows[0][5].get("apiName"), f"全文連結格式已變更: {rows[:1]}"
        detail = _mops(rows[0][5]["apiName"], rows[0][5]["parameters"])
        assert str(detail["code"]) == "200"
        d = detail["result"]["data"][0]
        assert len(d) >= 10 and d[1].count("/") == 2, f"全文欄位已變更: {d[:9]}"

    def test_market_day_list_carries_market_kind(self):
        resp = _mops("t05st02", {"year": FIXED_ROC_YEAR, "month": "06", "day": "02"})
        assert str(resp["code"]) == "200", f"t05st02 查詢失敗: {resp.get('message')}"
        names = leaf_titles(resp["result"].get("titles", []))
        assert names[:5] == ["發言日期", "發言時間", "公司代號", "公司名稱", "主旨"], f"欄位已變更: {names}"
        rows = resp["result"].get("data") or []
        assert rows and rows[0][5]["parameters"].get("marketKind") in ("sii", "otc", "rotc", "pub"), (
            f"市場別欄位已變更: {rows[:1]}"
        )


class TestInsiderHoldingsAPI:
    """stapap1（董監持股）與 query6_1（內部人持股異動）：tool 依欄位位置與 total 的鍵名取用。"""

    def test_board_holdings(self):
        resp = _mops("stapap1", {"companyId": FIXED_STOCK, "dataType": "2", "year": FIXED_ROC_YEAR,
                                 "month": "06", "subsidiaryCompanyId": ""})
        assert str(resp["code"]) == "200", f"stapap1 查詢失敗: {resp.get('message')}"
        parent = resp["result"]["parentCompany"]
        assert leaf_titles(parent["titles"])[:6] == ["職稱", "姓名", "選任時持股", "目前持股", "設質股數", "設質股數佔持股比例"]
        assert {"allDirectorSupervisor", "independentDirector", "nonIndependentDirector"} <= set(parent.get("total", {}))
        assert parent.get("data") and str(parent.get("yymm", "")).endswith("06")

    def test_monthly_changes_column_positions(self):
        resp = _mops("query6_1", {"companyId": FIXED_STOCK, "dataType": "2", "year": FIXED_ROC_YEAR,
                                  "month": "06", "subsidiaryCompanyId": ""})
        assert str(resp["code"]) == "200", f"query6_1 查詢失敗: {resp.get('message')}"
        cols = flatten_titles(resp["result"]["titles"])
        assert len(cols) == 24, f"欄位數已變更: {cols}"
        assert cols[4] == "上月實際持有股數" and cols[18] == "本月實際自有持有股數" and cols[21] == "截至本月底累計設質", cols
        assert cols[8].startswith("本月增加") and cols[13].startswith("本月減少"), cols


class TestTreasuryAndGuaranteesLegacyPages:
    """ajax_t35sc09（庫藏股）資料列固定 20 格；ajax_t05st11（背書保證/資金貸放）以無 id 的表格呈現。"""

    def _legacy(self, name: str, form: dict) -> str:
        body = fetch_bytes_or_skip(f"{MOPS_LEGACY_BASE}/{name}", method="POST",
                                   data={**MOPS_LEGACY_HIDDEN_FIELDS, **form})
        return body.decode("utf-8", errors="replace")

    def test_buyback_rows(self):
        from utils.mops import parse_html_tables
        from tools.mops.treasury_guarantees import BUYBACK_ROW_WIDTH

        html = self._legacy("ajax_t35sc09", {"TYPEK": "sii", "d1": "1140101", "d2": "1140331", "RD": "1"})
        rows = [r for t in parse_html_tables(html) for r in t if len(r) == BUYBACK_ROW_WIDTH and r[0].strip().isdigit()]
        assert rows, "固定歷史區間應有庫藏股資料，資料列寬度可能已變更"
        assert all(r[4].strip() in ("1", "2", "3") for r in rows), f"買回目的代碼已變更: {[r[4] for r in rows][:5]}"

    def test_lending_and_guarantee_tables(self):
        from utils.mops import parse_html_tables

        html = self._legacy("ajax_t05st11", {"co_id": "2317", "isnew": "false", "year": FIXED_ROC_YEAR, "month": "06"})
        text = " ".join(" ".join(r) for t in parse_html_tables(html) for r in t)
        assert "資金貸放餘額" in text and "背書保證" in text and "民國114年06月" in text, f"頁面內容已變更: {text[:200]}"
