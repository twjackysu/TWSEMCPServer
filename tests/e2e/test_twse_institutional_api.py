"""
測試 twse.com.tw/rwd/zh/fund/T86 上市三大法人買賣超 API。
只驗證 tools 中有寫死用到的欄位索引（IDX_*），
若 TWSE 調整欄位順序或移除欄位，測試會立即失敗。
"""

import pytest
from utils.api_client import TWSEAPIClient

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"

# Use a fixed historical trading day to ensure data stability
FIXED_DATE = "20250103"
FIXED_STOCK = "2330"  # TSMC

# Expected minimum number of columns per row (currently 19)
EXPECTED_MIN_COLUMNS = 19

# Expected fields in the `fields` array (order matters — tools rely on index positions)
EXPECTED_FIELDS_ORDER = [
    "證券代號",                               # IDX_CODE = 0
    "證券名稱",                               # IDX_NAME = 1
    "外陸資買進股數(不含外資自營商)",          # IDX_FK_BUY = 2
    "外陸資賣出股數(不含外資自營商)",          # IDX_FK_SELL = 3
    "外陸資買賣超股數(不含外資自營商)",        # IDX_FK_NET = 4
    "外資自營商買進股數",                      # IDX_FKDL_BUY = 5
    "外資自營商賣出股數",                      # IDX_FKDL_SELL = 6
    "外資自營商買賣超股數",                    # IDX_FKDL_NET = 7
    "投信買進股數",                            # IDX_IT_BUY = 8
    "投信賣出股數",                            # IDX_IT_SELL = 9
    "投信買賣超股數",                          # IDX_IT_NET = 10
    "自營商買賣超股數",                        # IDX_DL_NET = 11
    "自營商買進股數(自行買賣)",               # IDX_DL_BUY_SELF = 12
    "自營商賣出股數(自行買賣)",               # IDX_DL_SELL_SELF = 13
    "自營商買賣超股數(自行買賣)",             # IDX_DL_NET_SELF = 14
    "自營商買進股數(避險)",                   # IDX_DL_BUY_HEDGE = 15
    "自營商賣出股數(避險)",                   # IDX_DL_SELL_HEDGE = 16
    "自營商買賣超股數(避險)",                 # IDX_DL_NET_HEDGE = 17
    "三大法人買賣超股數",                      # IDX_TOTAL_NET = 18
]


class TestT86APIStructure:
    """驗證 T86 API 基本結構與欄位順序，防止 schema drift 造成 tools 取錯資料。"""

    def _fetch(self):
        return TWSEAPIClient.get_json(
            T86_URL,
            params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
        )

    def test_api_returns_ok(self):
        """確認 API 可達且回傳 stat=OK。"""
        result = self._fetch()
        assert result.get("stat") == "OK", f"API stat 異常: {result.get('stat')}"

    def test_api_has_data(self):
        """確認資料不為空。"""
        result = self._fetch()
        data = result.get("data", [])
        assert len(data) > 100, f"資料筆數異常，預期 >100 筆，實際: {len(data)}"

    def test_fields_count(self):
        """確認欄位數量至少 19 個（tools 最多使用到 index 18）。"""
        result = self._fetch()
        fields = result.get("fields", [])
        assert len(fields) >= EXPECTED_MIN_COLUMNS, (
            f"欄位數量不足！預期 >={EXPECTED_MIN_COLUMNS}，實際: {len(fields)}\n"
            f"欄位: {fields}"
        )

    def test_fields_order_matches_tool_indices(self):
        """確認欄位順序與 tools/history/institutional.py 中 IDX_* 常數一致。
        此測試是 schema drift 偵測的核心 — 若 TWSE 調整欄位順序，tools 會取到錯誤資料。
        """
        result = self._fetch()
        fields = result.get("fields", [])
        for idx, expected_field in enumerate(EXPECTED_FIELDS_ORDER):
            actual_field = fields[idx] if idx < len(fields) else "(missing)"
            assert actual_field == expected_field, (
                f"欄位 index {idx} 異動！\n"
                f"  預期: {expected_field}\n"
                f"  實際: {actual_field}\n"
                f"  完整欄位清單: {fields}"
            )

    def test_row_has_correct_column_count(self):
        """確認每筆資料 row 有足夠的欄位（防止資料結構縮減）。"""
        result = self._fetch()
        data = result.get("data", [])
        assert data, "data 為空"
        first_row = data[0]
        assert len(first_row) >= EXPECTED_MIN_COLUMNS, (
            f"資料 row 欄位不足！預期 >={EXPECTED_MIN_COLUMNS}，"
            f"實際: {len(first_row)}\n首筆資料: {first_row}"
        )


class TestT86APIStockFilter:
    """驗證特定股票資料可正確篩選（工具中 row[0] 為股票代號）。"""

    def _fetch(self):
        return TWSEAPIClient.get_json(
            T86_URL,
            params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
        )

    def test_stock_code_is_at_index_0(self):
        """確認 row[0] 為股票代號 (tools 用 row[IDX_CODE] 做篩選)。"""
        result = self._fetch()
        data = result.get("data", [])
        assert data, "data 為空"

        # Find TSMC
        tsmc_row = next((r for r in data if r[0] == FIXED_STOCK), None)
        assert tsmc_row is not None, (
            f"找不到台積電 {FIXED_STOCK}，確認 row[0] 仍為股票代號"
        )

    def test_tsmc_total_net_is_at_index_18(self):
        """確認 row[18] 為三大法人合計買賣超 (IDX_TOTAL_NET)，且為可解析的數字字串。"""
        result = self._fetch()
        data = result.get("data", [])
        tsmc_row = next((r for r in data if r[0] == FIXED_STOCK), None)
        assert tsmc_row is not None, f"找不到台積電 {FIXED_STOCK}"

        total_net_str = tsmc_row[18]
        try:
            int(total_net_str.replace(",", ""))
        except (ValueError, AttributeError):
            pytest.fail(
                f"row[18] (三大法人買賣超股數) 無法解析為整數，值為: {total_net_str}"
            )

    def test_foreign_net_is_at_index_4(self):
        """確認 row[4] 為外陸資買賣超股數 (IDX_FK_NET)，且為可解析的數字字串。"""
        result = self._fetch()
        data = result.get("data", [])
        tsmc_row = next((r for r in data if r[0] == FIXED_STOCK), None)
        assert tsmc_row is not None, f"找不到台積電 {FIXED_STOCK}"

        fk_net_str = tsmc_row[4]
        try:
            int(fk_net_str.replace(",", ""))
        except (ValueError, AttributeError):
            pytest.fail(
                f"row[4] (外陸資買賣超股數) 無法解析為整數，值為: {fk_net_str}"
            )
