"""
測試 twse.com.tw/rwd/zh/fund/T86 三大法人買賣超 API。
只驗證 tools 中有寫死用到的欄位索引，足以偵測來源 API 結構異動。
"""

from utils.api_client import TWSEAPIClient

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電，流動性高必有法人進出

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"


def _fetch(date=FIXED_DATE):
    return TWSEAPIClient.get_json(
        T86_URL,
        params={"response": "json", "date": date, "selectType": "ALL"},
    )


class TestT86API:
    """T86 三大法人買賣超日報 API 結構測試。

    tool 依賴的欄位索引：
      row[0]  證券代號（get_by_stock 篩選用）
      row[18] 三大法人合計買賣超（summary 排序 / 過濾用）
    """

    def test_api_returns_ok_with_data(self):
        """API 可達，stat=OK，有資料列."""
        result = _fetch()
        assert result.get("stat") == "OK"
        assert len(result.get("data", [])) > 0

    def test_standard_rows_have_19_columns(self):
        """主力資料列應為 19 欄，確保 row[18]（IDX_TOTAL_NET）可存取."""
        result = _fetch()
        rows_19 = [r for r in result["data"] if len(r) == 19]
        assert len(rows_19) > 0, "找不到 19 欄資料列，欄位結構可能已變更"

    def test_stock_code_at_index_0_and_total_net_at_index_18(self):
        """row[0] 應為股票代號，row[18] 應可解析為整數（兩個 tool 的核心依賴）."""
        result = _fetch()
        tsmc = next((r for r in result["data"] if len(r) == 19 and r[0] == FIXED_STOCK), None)
        assert tsmc is not None, f"{FIXED_STOCK} 不在資料中，row[0] 可能已不再是股票代號"
        int(tsmc[18].replace(",", ""))  # 拋出 ValueError 即代表欄位位移
