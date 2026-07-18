"""
測試 www.twse.com.tw/rwd 五個新增歷史查詢 API（NEW_TOOLS_PLAN.md Tier 2 TWSE 半）。
只驗證 tools 中有寫死用到的欄位索引/位置，足以偵測來源 API 結構異動。
"""

import pytest
from tests.helpers import fetch_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電


class TestStockMonthlyHistoryAPI:
    """個股月成交資訊 - FMSRFK
    Tool get_stock_monthly_history 使用 row[0]~row[8]：
    年度、月份、最高價、最低價、加權平均價、成交筆數、成交金額、成交股數、週轉率。
    """

    def test_row_has_9_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/FMSRFK",
            params={"response": "json", "date": FIXED_DATE, "stockNo": FIXED_STOCK},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        assert len(data[0]) == 9, f"欄位數不為 9，row 結構可能已變更: {data[0]}"


class TestStockYearlyHistoryAPI:
    """個股歷年成交資訊 - FMNPTK
    Tool get_stock_yearly_history 使用 tables[0] 的 row[0]~row[8]：
    年度、成交股數、成交金額、成交筆數、最高價、日期、最低價、日期、收盤平均價。
    """

    def test_yearly_table_exists_with_9_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/FMNPTK",
            params={"response": "json", "date": FIXED_DATE, "stockNo": FIXED_STOCK},
        )
        assert result.get("stat") == "OK"
        tables = result.get("tables", [])
        assert len(tables) > 0, "tables 結構可能已變更"
        data = tables[0].get("data", [])
        assert len(data) > 0
        assert len(data[0]) == 9, f"欄位數不為 9，tables[0] row 結構可能已變更: {data[0]}"


class TestBlockTradesDetailAPI:
    """鉅額交易日成交資訊 - BFIAUU
    Tool get_block_trades_detail 使用 row[0]~row[5]：
    證券代號、證券名稱、交易別、成交價、成交股數、成交金額。
    此端點無伺服器端股票代號篩選，tool 於本地端以 row[0] 過濾。
    """

    def test_row_has_6_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/block/BFIAUU",
            params={"response": "json", "date": FIXED_DATE},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        assert len(data[0]) == 6, f"欄位數不為 6，row 結構可能已變更: {data[0]}"


class TestShortSaleLendingBalanceHistoryAPI:
    """信用額度總量管制餘額表 - TWT93U
    Tool get_short_sale_lending_balance_history 使用 row[0]~row[13]：
    代號、名稱、融券(前日餘額/賣出/買進/現券/今日餘額/次一營業日限額)、
    借券(前日餘額/當日賣出/當日還券/當日調整/當日餘額/次一營業日可限額)。
    """

    def test_row_has_at_least_14_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U",
            params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        assert len(data[0]) >= 14, f"欄位數不足 14，row 結構可能已變更: {data[0]}"


class TestShortSaleLendingTradesHistoryAPI:
    """當日融券賣出與借券賣出成交量值 - TWTASU
    Tool get_short_sale_lending_trades_history 使用 row[0]~row[4]：
    證券名稱(含代號，以空白分隔)、融券賣出數量、融券賣出金額、借券賣出數量、借券賣出金額。
    """

    def test_row_has_5_columns_and_code_embedded_in_name(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU",
            params={"response": "json", "date": FIXED_DATE},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        assert len(data[0]) == 5, f"欄位數不為 5，row 結構可能已變更: {data[0]}"
        tsmc = next((r for r in data if r[0].split(None, 1)[0] == FIXED_STOCK), None)
        assert tsmc is not None, f"{FIXED_STOCK} 不在資料中，row[0] 的代號+名稱格式可能已變更"
