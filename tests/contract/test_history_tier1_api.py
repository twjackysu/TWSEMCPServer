"""
測試 www.twse.com.tw/rwd 五個新增歷史查詢 API（NEW_TOOLS_PLAN.md Tier 1）。
只驗證 tools 中有寫死用到的欄位索引/位置，足以偵測來源 API 結構異動。
"""

import pytest
from sources.twse.mi_index import stock_quotes
from sources.twse.mi_qfiis import foreign_holdings
from tests.helpers import fetch_or_skip, gateway_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定


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

    @pytest.mark.parametrize("params", [
        # 週資料用該週第一個交易日查詢；2026-04-06（週一）休市，該週從 04-07 開始
        {"type": "week", "weekDate": "20260407"},
        {"type": "month", "monthDate": "20260915"},
    ])
    def test_week_and_month_periods(self, params):
        result = fetch_or_skip("https://www.twse.com.tw/rwd/zh/fund/BFI82U", params={"response": "json", **params})
        assert result.get("stat") == "OK", f"{params} 不再回傳資料: {result.get('stat')}"
        data = result.get("data", [])
        assert data and all(len(r) >= 4 for r in data), f"{params} row 結構已變更（tool 讀 row[0]~row[3]）: {data[:1]}"


class TestMiIndexQuotesGateway:
    """全市場每日收盤行情 - MI_INDEX（sources/twse/mi_index.py stock_quotes）
    get_stock_daily_trading、services/market_snapshot（選股、同業比較）都只透過這個 gateway 讀行情表；
    真實回應要能建出 QuoteTable，欄位改名時 gateway 丟 UpstreamFormatError。
    """

    def test_fixed_day_parses_into_typed_quotes(self):
        table = gateway_or_skip(stock_quotes, "ALLBUT0999", FIXED_DATE)
        assert table is not None and table.date == FIXED_DATE, "固定歷史交易日應有每日收盤行情"
        assert table.group.startswith("全部"), f"行情表標題格式已變更: {table.title!r}"
        tsmc = next((q for q in table.quotes if q.code == "2330"), None)
        assert tsmc and tsmc.name == "台積電"
        assert None not in (tsmc.open, tsmc.high, tsmc.low, tsmc.close, tsmc.volume, tsmc.value, tsmc.transactions), (
            f"數字格式已變更：{tsmc}")
        # gateway 從漲跌(+/-) 欄的 HTML 取出正負號
        directions = {q.direction for q in table.quotes}
        assert directions <= {"+", "-", "", "X"} and directions & {"+", "-"}, f"漲跌(+/-) 欄格式已變更: {directions}"


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


class TestForeignHoldingsGateway:
    """get_foreign_holdings 只透過 sources/twse/mi_qfiis.py 讀；欄位依名稱取（2009-04-30 以前是「外資」名稱），
    欄位改名會丟 UpstreamFormatError。"""

    @pytest.mark.parametrize("day", [FIXED_DATE, "20050103"])
    def test_fixed_day_parses(self, day):
        report = gateway_or_skip(foreign_holdings, day)
        assert report is not None and report.holdings, f"固定歷史交易日 {day} 應有資料"
        h = report.holdings[0]
        assert None not in (h.issued_shares, h.available_shares, h.held_shares, h.available_pct, h.held_pct,
                            h.limit_pct), f"數字格式已變更：{h}"
