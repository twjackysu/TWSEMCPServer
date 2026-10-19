"""
測試 twse.com.tw/rwd/zh/fund/T86 三大法人買賣超 API。
只驗證 tools 中有寫死用到的欄位索引，足以偵測來源 API 結構異動。
"""

import pytest
from tests.helpers import fetch_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電，流動性高必有法人進出

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"


@pytest.fixture(scope="class")
def t86_data():
    return fetch_or_skip(
        T86_URL,
        params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
    )


class TestT86API:
    """T86 三大法人買賣超日報 API 結構測試。

    tool 依賴的欄位索引：
      row[0]  證券代號（get_by_stock 篩選用）
      row[18] 三大法人合計買賣超（summary 排序 / 過濾用）
    """

    def test_standard_rows_have_19_columns(self, t86_data):
        """主力資料列應為 19 欄，確保 row[18]（IDX_TOTAL_NET）可存取."""
        assert t86_data.get("stat") == "OK"
        rows_19 = [r for r in t86_data["data"] if len(r) == 19]
        assert len(rows_19) > 0, "找不到 19 欄資料列，欄位結構可能已變更"

    def test_stock_code_at_index_0_and_total_net_at_index_18(self, t86_data):
        """row[0] 應為股票代號，row[18] 應可解析為整數（兩個 tool 的核心依賴）."""
        assert t86_data.get("stat") == "OK"
        tsmc = next((r for r in t86_data["data"] if len(r) == 19 and r[0] == FIXED_STOCK), None)
        assert tsmc is not None, f"{FIXED_STOCK} 不在資料中，row[0] 可能已不再是股票代號"
        int(tsmc[18].replace(",", ""))  # 拋出 ValueError 即代表欄位位移


class TestT86SelectType:
    """get_twse_institutional_investors_summary 的 category 直接對應 selectType：預設 ALLBUT0999（不含權證），
    etf＝0099P，產業代碼原樣傳入；category="stock" 從 ALLBUT0999 去掉 00 開頭代號，依賴「ETF 皆為 00 開頭」."""

    @staticmethod
    def _codes(select_type: str) -> set:
        resp = fetch_or_skip(T86_URL, params={"response": "json", "date": FIXED_DATE, "selectType": select_type})
        assert resp.get("stat") == "OK", f"selectType={select_type} 不再被接受: {resp.get('stat')}"
        return {row[0].strip() for row in resp.get("data") or []}

    def test_select_types_filter(self):
        everything, no_warrants = self._codes("ALL"), self._codes("ALLBUT0999")
        assert no_warrants < everything, "ALLBUT0999 不再是 ALL 的子集（排除權證的篩選失效）"
        semiconductor = self._codes("24")
        assert semiconductor and semiconductor < no_warrants, "產業代碼 selectType 不再篩選"

    def test_etf_codes_are_exactly_the_00_prefixed_rows(self):
        etf, no_warrants = self._codes("0099P"), self._codes("ALLBUT0999")
        assert etf and etf == {c for c in no_warrants if c.startswith("00")}, (
            "ETF 與 00 開頭代號不再一一對應，category=stock 的排除規則需要調整"
        )
