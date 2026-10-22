"""公開資訊觀測站 (MOPS) contract tests.

The MOPS JSON API (mops.twse.com.tw/mops/api/*) is the SPA's private backend with no
public docs, so it can change without notice. These tests pin down exactly what
tools/mops/ relies on: request field names, the ``code``/``result`` envelope, the
``titles`` + rows table shape, the column names the dividend tool looks up, and what the
sources/mops gateways parse.
"""

from datetime import date

import pytest

from sources.mops.insiders import board_holdings, insider_changes
from sources.mops.investor_conference import investor_conferences
from sources.mops.major_news import company_news, market_news, news_detail
from sources.mops.t35sc09 import treasury_buybacks
from tests.helpers import fetch_or_skip, fetch_bytes_or_skip, gateway_or_skip
from tools.mops.dividend import KEY_COLUMNS
from sources.mops.monthly_revenue import CURRENT_MONTH_LABEL, monthly_revenue
from utils.mops import (
    MOPS_API_BASE,
    MOPS_LEGACY_BASE,
    MOPS_LEGACY_HIDDEN_FIELDS,
    flatten_titles,
    leaf_titles,
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
        future_roc_year = str(date.today().year - 1911 + 2)  # contract-ok: 組請求參數（未來的民國年），不是驗資料
        resp = _mops("t164sb04", _statement_body(future_roc_year))
        assert str(resp["code"]) == "406", (
            f"查詢尚未公告的季度不再回 406（實際 {resp['code']} {resp.get('message')}），"
            f"mops_post 的「查無資料」判斷需要更新"
        )


class TestMonthlyRevenueGateway:
    """t05st10_ifrs 只透過 sources/mops/monthly_revenue.py 讀；欄位依 titles（項目、營業收入淨額）取，改名時 gateway 丟
    UpstreamFormatError。工具以「本月」那一項算月增率。"""

    def test_fixed_month_parses(self):
        report = gateway_or_skip(monthly_revenue, FIXED_STOCK, 2025, 8)  # 民國 114 年（FIXED_ROC_YEAR）
        assert report is not None and report.items, "查詢固定歷史月份應有月營收"
        assert report.period == (2025, 8), f"查詢的月份沒有被採用：{report.period}"
        assert report.current is not None, f"沒有「{CURRENT_MONTH_LABEL}」一項或數字格式已變更：{report.items[:2]}"

    def test_latest_mode_returns_its_month(self):
        """tool 不帶月份時送 dataType=1 + 空 year/month，並以 yymm 推算前一個月."""
        report = gateway_or_skip(monthly_revenue, FIXED_STOCK)
        assert report is not None and report.period is not None, "最新月份查詢不再回傳 yymm"


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


class TestInvestorConferenceGateway:
    """ajax_t100sb02_1 只透過 sources/mops/investor_conference.py 讀：table#myTable 兩列表頭（法人說明會簡報內容 下分
    中文檔案／英文檔案），欄位依名稱取，表頭改了 gateway 丟 UpstreamFormatError。"""

    def test_fixed_month_parses(self):
        """月份由 gateway 補零（"07"）送出；不補零 MOPS 回查無資料."""
        rows = gateway_or_skip(investor_conferences, "sii", int(FIXED_ROC_YEAR), 7)
        assert rows, f"民國{FIXED_ROC_YEAR}年07月 應有法說會資料"

    @pytest.mark.parametrize("market", ["otc", "rotc", "pub"])
    def test_other_markets_parse(self, market):
        """興櫃與公開發行的頁面網站欄名不同（公司網站是否提供法人說明會內容）、沒有影音連結資訊."""
        rows = gateway_or_skip(investor_conferences, market, int(FIXED_ROC_YEAR), 7)
        assert rows, f"{market} 民國{FIXED_ROC_YEAR}年07月 應有法說會資料"

    def test_company_filter_is_server_side(self):
        rows = gateway_or_skip(investor_conferences, "sii", int(FIXED_ROC_YEAR), None, FIXED_STOCK)
        assert rows, f"{FIXED_STOCK} 在民國{FIXED_ROC_YEAR}年應有法說會資料"
        assert {c.code for c in rows} == {FIXED_STOCK}, "co_id 不再於伺服器端篩選"

    def test_no_data_page_says_so(self):
        """沒有資料回「查無資料」頁，gateway 回 []（工具回查無）；改了措辭會變成非預期頁面的錯誤."""
        assert gateway_or_skip(investor_conferences, "sii", int(FIXED_ROC_YEAR), 1, "9999") == []


class TestMajorNewsGateway:
    """t05st01（公司年度）/ t05st02（某日全市場）/ *_detail（全文）只透過 sources/mops/major_news.py 讀；欄位依
    titles 取，改名時 gateway 丟 UpstreamFormatError。工具靠「詳細資料」的連結取全文、靠它的 marketKind 分市場。"""

    def test_company_year_list_and_detail(self):
        news = gateway_or_skip(company_news, FIXED_STOCK, int(FIXED_ROC_YEAR))
        assert news is not None and news.announcements, "固定歷史年度應有重大訊息"
        a = next((a for a in news.announcements if a.link), None)
        assert a is not None, "「詳細資料」不再是 {apiName, parameters} 連結"
        assert gateway_or_skip(news_detail, a.link) is not None, f"{a.link.api_name} 查無全文"

    def test_market_day_list_carries_market_kind(self):
        rows = gateway_or_skip(market_news, "20250602")  # 民國 114 年（FIXED_ROC_YEAR）
        assert rows, "固定歷史交易日應有重大訊息"
        assert {a.market for a in rows} <= {"sii", "otc", "rotc", "pub"}, "市場別（marketKind）的值已變更（工具以此篩選）"


class TestInsiderHoldingsGateway:
    """stapap1（董監持股）與 query6_1（內部人持股異動）只透過 sources/mops/insiders.py 讀；欄位依 titles 取（異動的
    「本月增加」「本月減少」兩組依群組名），改名時 gateway 丟 UpstreamFormatError。工具依 total 的鍵名標示合計。"""

    def test_board_holdings(self):
        report = gateway_or_skip(board_holdings, FIXED_STOCK, int(FIXED_ROC_YEAR), 6)
        assert report is not None and report.holdings, "固定歷史月份應有董監持股"
        assert report.yymm.endswith("06"), f"查詢的月份沒有被採用：{report.yymm}"
        assert {"allDirectorSupervisor", "independentDirector", "nonIndependentDirector"} <= set(report.totals), (
            f"total 的鍵名已變更（工具以此標示）：{sorted(report.totals)}")

    def test_monthly_changes(self):
        report = gateway_or_skip(insider_changes, FIXED_STOCK, int(FIXED_ROC_YEAR), 6)
        assert report is not None and report.changes, "固定歷史月份應有內部人申報"
        c = report.changes[0]
        assert None not in (c.last_month, c.this_month, c.pledged), f"數字格式已變更：{c}"
        assert {t.split(" ", 1)[0] for t, _ in c.moves} == {"本月增加", "本月減少"}, "異動欄位的群組已變更"


class TestTreasuryAndGuaranteesLegacyPages:
    """ajax_t35sc09（庫藏股）只透過 sources/mops/t35sc09.py 讀，欄位依表頭名稱取，表頭改了 gateway 丟
    UpstreamFormatError；ajax_t05st11（背書保證/資金貸放）以無 id 的表格呈現。"""

    def _legacy(self, name: str, form: dict) -> str:
        body = fetch_bytes_or_skip(f"{MOPS_LEGACY_BASE}/{name}", method="POST",
                                   data={**MOPS_LEGACY_HIDDEN_FIELDS, **form})
        return body.decode("utf-8", errors="replace")

    def test_buyback_gateway(self):
        rows = gateway_or_skip(treasury_buybacks, "sii", "20250101", "20250331")
        assert rows, "固定歷史區間應有庫藏股資料"
        assert {b.purpose for b in rows} <= {"1", "2", "3"}, "買回目的代碼已變更（工具以此標示）"
        b = next((b for b in rows if b.bought_shares is not None), None)
        assert b is not None, "固定歷史區間應有執行完畢的案件"
        assert None not in (b.amount_cap, b.planned_shares, b.price_low, b.price_high, b.pct_of_planned,
                            b.bought_amount, b.average_price, b.pct_of_issued), f"數字格式已變更：{b}"

    def test_buyback_range_without_data_says_so(self):
        """沒有案件的區間回「查無所需資料」頁，gateway 回 None（工具回查無）；改了措辭會變成非預期頁面的錯誤."""
        assert gateway_or_skip(treasury_buybacks, "rotc", "20250101", "20251231") is None

    def test_lending_and_guarantee_tables(self):
        from utils.mops import parse_html_tables

        html = self._legacy("ajax_t05st11", {"co_id": "2317", "isnew": "false", "year": FIXED_ROC_YEAR, "month": "06"})
        text = " ".join(" ".join(r) for t in parse_html_tables(html) for r in t)
        assert "資金貸放餘額" in text and "背書保證" in text and "民國114年06月" in text, f"頁面內容已變更: {text[:200]}"
