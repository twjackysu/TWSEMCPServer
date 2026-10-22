"""
測試 www.twse.com.tw/rwd 五個新增歷史查詢 API（NEW_TOOLS_PLAN.md Tier 2 TWSE 半）。
只驗證 tools 中有寫死用到的欄位索引/位置，足以偵測來源 API 結構異動。
"""

import pytest

from sources.twse.bfiauu import BFIAUU_URL, block_trades
from sources.twse.twt93u import TWT93U_URL, short_sale_lending_balances
from tests.helpers import fetch_or_skip, gateway_or_skip
from utils.constants import SUMMARY_ROW_LABELS

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電


class TestStockMonthlyHistoryAPI:
    """個股月成交資訊 - FMSRFK
    Tool get_stock_monthly_trading 使用 row[0]~row[8]：
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
    Tool get_stock_yearly_trading 使用 tables[0] 的 row[0]~row[8]：
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


class TestBlockTradesGateway:
    """鉅額交易日成交資訊 - BFIAUU（sources/twse/bfiauu.py）
    get_block_trades_detail 只透過這個 gateway 讀；欄位依名稱取，欄位改名時 gateway 丟 UpstreamFormatError。
    2011-12-16 以前多一欄「交割期別」，兩種格式各驗一天能讀。
    """

    @pytest.mark.parametrize("day", [FIXED_DATE, "20100104"])
    def test_fixed_day_parses(self, day):
        trades = gateway_or_skip(block_trades, day)
        assert trades is not None and trades.trades, f"{day} 應有鉅額交易"
        t = trades.trades[0]
        assert None not in (t.price, t.volume, t.value), f"數字格式已變更：{t}"

    def test_last_row_is_the_total(self):
        """gateway 以證券代號欄的「總計」濾掉末列；標籤改了，總計就會被當成一筆鉅額交易."""
        result = fetch_or_skip(BFIAUU_URL, params={"response": "json", "date": FIXED_DATE})
        assert result["data"][-1][0].strip() in SUMMARY_ROW_LABELS, f"末列不再是彙總列: {result['data'][-1]}"


class TestShortSaleLendingGateway:
    """信用額度總量管制餘額表 - TWT93U（sources/twse/twt93u.py）
    get_short_sale_lending_balance_history 只透過這個 gateway 讀；欄位依 groups 的組名＋欄名取，groups 或欄位
    改了 gateway 丟 UpstreamFormatError。2012-03-16 以前借券是另一組欄位，兩種格式各驗一天能讀。
    """

    @pytest.mark.parametrize("day", [FIXED_DATE, "20100104"])
    def test_fixed_day_parses(self, day):
        balances = gateway_or_skip(short_sale_lending_balances, day)
        assert balances is not None and balances.rows, f"{day} 應有資料"
        r = balances.rows[0]
        assert None not in (r.short.previous, r.short.today, r.lending.previous, r.lending.today), f"數字格式已變更：{r}"

    def test_last_row_is_the_total(self):
        """gateway 以名稱欄的「合計」濾掉末列；標籤改了，合計就會被當成一支股票."""
        result = fetch_or_skip(TWT93U_URL, params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"})
        assert result["data"][-1][1].strip() in SUMMARY_ROW_LABELS, f"末列不再是彙總列: {result['data'][-1]}"


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

    def test_last_row_is_summary(self):
        """tool 以 row[0] split 後的第一段濾掉末列「合計」."""
        result = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU",
            params={"response": "json", "date": FIXED_DATE},
        )
        assert result["data"][-1][0].split(None, 1)[0] in SUMMARY_ROW_LABELS, (
            f"末列不再是彙總列: {result['data'][-1]}"
        )
