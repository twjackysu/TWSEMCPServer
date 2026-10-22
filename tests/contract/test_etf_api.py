"""Contract tests for the ETF tools' sources (tools/etf/).

- SITCA ETF zone (utils/sitca.py): query pages' ddlYM month list; result pages
  etf_info2 / etf_statement2 read by GridView id and column name; filter by 證券代號 and,
  for the older months without codes, by 基金統編.
- TWSE MIS all_etf.txt: per-issuer groups of single-letter fields.
- TPEx website ETF/list and ETF/detail (form POST, JSON).
- SITCA 基金投資明細 IN2629 (monthly top 10) / IN2630 (quarterly >1%): period postback + query by
  class, result columns read by name, and fund names that join with the ETF zone's names.
t187ap47_L fields are covered by tests/contract/test_api_schemas.py via tool_field_dependencies.py.
"""

import re

import pytest

from sources.tpex.etf import ETF_TYPES, tpex_etf_detail, tpex_etfs
from tests.helpers import fetch_or_skip, gateway_or_skip
from tools.etf.daily_nav import MIS_ALL_ETF_URL
from tools.etf.holdings import REQUIRED_COLUMNS as HOLDINGS_COLUMNS
from tools.etf.monthly_stats import records
from utils.api_client import TWSEAPIClient
from utils.sitca import (
    HOLDINGS_MONTHLY_PAGE,
    HOLDINGS_QUARTERLY_PAGE,
    available_months,
    fund_name_key,
    holdings_by_class,
    holdings_months,
    query_rows,
)

# A month that has 證券代號 and one that predates them (codes "-", only 基金統編).
FIXED_MONTH_WITH_CODES = "202501"
FIXED_MONTH_WITHOUT_CODES = "202001"
TW50_FUND_ID = "98764389"  # 元大台灣卓越50基金 (0050)
# Older than the default (latest) period, so the period postback is exercised.
FIXED_HOLDINGS_MONTH = "202501"
FIXED_HOLDINGS_QUARTER = "202503"
INFO_COLUMNS = ["證券代號", "證券簡稱", "經理公司", "基金名稱", "基金成立日期", "分類", "追蹤指數", "是否有發行 配息級別"]


@pytest.fixture(scope="module")
def client():
    return TWSEAPIClient.get_instance()


class TestSitcaEtfZone:
    def test_query_pages_offer_months(self, client):
        # available_months raises when the ddlYM select is gone
        statement_months = available_months(client, "etf_statement.aspx")
        assert statement_months == sorted(statement_months, reverse=True)
        assert FIXED_MONTH_WITH_CODES in statement_months and FIXED_MONTH_WITHOUT_CODES in statement_months
        available_months(client, "etf_info.aspx")

    def test_info_result_columns_and_code_filter(self, client):
        ym = available_months(client, "etf_info.aspx")[0]
        rows = query_rows(client, "etf_info2.aspx", ym, code="0050")
        assert rows, "etf_info2 找不到 GridView1 表格或表頭不再以「序號」開頭"
        missing = [c for c in INFO_COLUMNS if c not in rows[0]]
        assert not missing, f"etf_info2 欄位已變更，缺少 {missing}: {rows[0]}"
        assert len(rows) == 2 and dict(zip(rows[0], rows[1], strict=True))["證券代號"] == "0050", "txtemcode 代號篩選失效"

    def test_statement_columns_and_code_filter(self, client):
        rows = records(query_rows(client, "etf_statement2.aspx", FIXED_MONTH_WITH_CODES, code="0050"))  # raises on missing columns
        assert [r["證券代號"] for r in rows] == ["0050"], "txtemcode 代號篩選失效"

    def test_statement_fund_id_filter_for_months_without_codes(self, client):
        rows = records(query_rows(client, "etf_statement2.aspx", FIXED_MONTH_WITHOUT_CODES, fund_id=TW50_FUND_ID))
        assert len(rows) == 1 and rows[0]["基金統編"] == TW50_FUND_ID, "txtfund 基金統編篩選失效"

    def test_statement_whole_market(self, client):
        rows = records(query_rows(client, "etf_statement2.aspx", FIXED_MONTH_WITH_CODES))
        assert len({r["基金統編"] for r in rows}) > 1, "不帶篩選條件時不再回傳全部 ETF"


class TestMisAllEtf:
    def test_structure(self):
        payload = fetch_or_skip(MIS_ALL_ETF_URL)
        groups = payload.get("a1")
        assert isinstance(groups, list) and groups, f"all_etf.txt 不再有 a1 群組: {str(payload)[:200]}"
        items = [i for g in groups for i in (g.get("msgArray") or [])]
        if not items:
            pytest.skip("all_etf.txt 目前沒有任何 ETF（上游無資料，非 interface 變更）")
        missing = {k for k in "abcdefghij" if any(k not in i for i in items)}
        assert not missing, f"all_etf.txt 欄位已變更，缺少 {sorted(missing)}"
        bad = [i["a"] for i in items if not re.fullmatch(r"\d{4,6}[A-Z]?", str(i["a"]).strip())]
        assert not bad, f"all_etf.txt 的 a 欄不再是 ETF 代號: {bad[:5]}"


class TestTpexEtfPages:
    """ETF/list 與 ETF/detail 只透過 sources/tpex/etf.py 讀：清單的證券代號依欄名取，規格表每張一列、欄位與值逐一配對；
    欄名或結構改了 gateway 丟 UpstreamFormatError。工具依代號在三種類型的清單中找出 type 再查規格."""

    @pytest.mark.parametrize("etf_type", ETF_TYPES)
    def test_list_types(self, etf_type):
        etfs = gateway_or_skip(tpex_etfs, etf_type)
        assert etfs, f"ETF/list({etf_type}) 沒有任何 ETF"

    def test_bond_list_and_detail(self):
        assert any(e.code == "00679B" for e in gateway_or_skip(tpex_etfs, "bond")), "00679B 不在 ETF/list(bond)"
        sections = gateway_or_skip(tpex_etf_detail, "bond", "00679B")
        spec = next((s for s in sections if s.title == "商品規格"), None)
        assert spec is not None and ("證券代號", "00679B") in spec.items, f"ETF/detail 商品規格表已變更: {sections!r:.300}"


class TestSitcaHoldings:
    """get_etf_holdings 先在 ETF 專區用代號找到基金名稱與類型代號，再到基金投資明細依類別查詢並比對名稱。"""

    @staticmethod
    def _zone_names(client, ym, fund_class):
        rows = records(query_rows(client, "etf_statement2.aspx", ym))
        return {fund_name_key(r["基金名稱"]) for r in rows if r["類型代號"] == fund_class}

    def test_period_lists(self, client):
        monthly = holdings_months(client, HOLDINGS_MONTHLY_PAGE)  # raises when the select is gone
        quarterly = holdings_months(client, HOLDINGS_QUARTERLY_PAGE)
        assert FIXED_HOLDINGS_MONTH in monthly and FIXED_HOLDINGS_QUARTER in quarterly

    def test_monthly_columns_and_period_postback(self, client):
        header, funds = holdings_by_class(client, HOLDINGS_MONTHLY_PAGE, FIXED_HOLDINGS_MONTH, "AH11")
        missing = [c for c in HOLDINGS_COLUMNS if c not in header]
        assert not missing, f"IN2629 欄位已變更，缺少 {missing}: {header}"
        # 沒做期間 postback 時伺服器會回第一家投信的全部基金，而不是該類別的 ETF
        tw50 = [rows for name, rows in funds.items() if fund_name_key(name) == "元大台灣卓越50基金"]
        assert tw50, f"IN2629 {FIXED_HOLDINGS_MONTH} AH11 找不到元大台灣卓越50基金，期間或類別條件可能失效: {list(funds)[:5]}"
        assert all(len(r) == len(header) - 1 for r in tw50[0]), "持股列寬與表頭不符（rowspan 結構可能已變更）"

    def test_quarterly_columns(self, client):
        header, funds = holdings_by_class(client, HOLDINGS_QUARTERLY_PAGE, FIXED_HOLDINGS_QUARTER, "AH11")
        missing = [c for c in HOLDINGS_COLUMNS if c not in header]
        assert not missing, f"IN2630 欄位已變更，缺少 {missing}: {header}"
        assert any(fund_name_key(n) == "元大台灣卓越50基金" for n in funds)

    @pytest.mark.parametrize("fund_class", ["AH11", "AH22"])
    def test_fund_names_join_with_etf_zone(self, client, fund_class):
        """基金投資明細沒有證券代號，工具靠名稱對回 ETF 專區；兩邊命名規則一變就對不上。"""
        _header, funds = holdings_by_class(client, HOLDINGS_MONTHLY_PAGE, FIXED_HOLDINGS_MONTH, fund_class)
        zone = self._zone_names(client, FIXED_HOLDINGS_MONTH, fund_class)
        unmatched = [n for n in funds if fund_name_key(n) not in zone]
        assert funds and not unmatched, f"基金投資明細的基金名稱對不回 ETF 專區: {unmatched[:5]}"
