"""
測試 www.twse.com.tw/rwd 五個新增歷史查詢 API（NEW_TOOLS_PLAN.md Tier 1）。
只驗證 tools 中有寫死用到的欄位索引/位置，足以偵測來源 API 結構異動。
"""

import pytest
from tests.helpers import fetch_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電


class TestMarketInstitutionalAmountsAPI:
    """三大法人買賣金額統計 - BFI82U
    Tool get_market_institutional_amounts_history 使用 row[0]~row[3]：
    單位名稱、買進金額、賣出金額、買賣差額。
    """

    def test_row_has_name_and_three_amount_fields(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/fund/BFI82U",
            params={"response": "json", "dayDate": FIXED_DATE, "type": "day"},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        row = data[0]
        assert len(row) >= 4, f"欄位數不足 4，row 結構可能已變更: {row}"
        assert "合計" in [r[0] for r in data], "找不到「合計」列，row[0] 單位名稱欄位可能已變更"


class TestAllStocksDailyCloseAPI:
    """全市場每日收盤行情 - MI_INDEX
    Tool get_all_stocks_daily_close 從 tables 中找標題含「每日收盤行情」的 table，
    使用該 table 的 row[0]~row[15]：代號、名稱、量、筆數、金額、開高低收、漲跌、
    漲跌價差、買賣揭示、本益比。
    """

    def test_stock_table_exists_with_16_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
            params={"response": "json", "date": FIXED_DATE, "type": "ALLBUT0999"},
        )
        assert result.get("stat") == "OK"
        tables = result.get("tables", [])
        stock_table = next(
            (t for t in tables if "每日收盤行情" in (t.get("title") or "")), None
        )
        assert stock_table is not None, "找不到標題含「每日收盤行情」的 table，tables 結構可能已變更"
        data = stock_table.get("data", [])
        assert len(data) > 0
        assert len(data[0]) >= 16, f"欄位數不足 16，row 結構可能已變更: {data[0]}"


class TestMarketTurnoverHistoryAPI:
    """每日市場成交資訊 - FMTQIK
    Tool get_market_turnover_history 使用 row[0]~row[5]：
    日期、成交股數、成交金額、成交筆數、加權指數、漲跌點數。
    """

    def test_row_has_6_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK",
            params={"response": "json", "date": FIXED_DATE},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        assert len(data[0]) == 6, f"欄位數不為 6，row 結構可能已變更: {data[0]}"


class TestTaiexIndexHistoryAPI:
    """加權股價指數歷史 - MI_5MINS_HIST
    Tool get_taiex_index_history 使用 row[0]~row[4]：
    日期、開盤指數、最高指數、最低指數、收盤指數。
    """

    def test_row_has_5_columns(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST",
            params={"response": "json", "date": FIXED_DATE},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        assert len(data[0]) == 5, f"欄位數不為 5，row 結構可能已變更: {data[0]}"


class TestForeignHoldingsHistoryAPI:
    """外資及陸資持股統計 - MI_QFIIS
    Tool get_foreign_holdings_history 使用 row[0],row[1],row[3]~row[7]：
    代號、名稱、發行股數、尚可投資股數、持有股數、尚可投資比率、持股比率。
    """

    def test_row_has_stock_code_and_holding_fields(self):
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS",
            params={"response": "json", "date": FIXED_DATE, "selectType": "ALLBUT0999"},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        tsmc = next((r for r in data if r[0] == FIXED_STOCK), None)
        assert tsmc is not None, f"{FIXED_STOCK} 不在資料中，row[0] 可能已不再是股票代號"
        assert len(tsmc) >= 8, f"欄位數不足 8，row 結構可能已變更: {tsmc}"
        float(str(tsmc[7]))  # 持股比率需可轉數字，拋出例外即代表欄位位移
