"""
測試 twse.com.tw/exchangeReport 歷史行情 API。
只驗證 tools 中有寫死用到的欄位（如日期格式、價格欄位索引），
不額外測試未使用的欄位或 schema 完整性。
"""

import pytest
from utils.api_client import TWSEAPIClient

# Use a fixed historical trading day to ensure data stability
FIXED_DATE = "20250103"
FIXED_STOCK = "2330"  # TSMC


class TestStockDayAPI:
    """個股歷史日K - STOCK_DAY
    Tool get_stock_history 使用 row[0] 作為日期（需 ROC 格式含 /），
    row[1]~row[8] 作為成交量、金額、開高低收、漲跌、筆數。
    """

    URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

    def _fetch(self):
        return TWSEAPIClient.get_json(
            self.URL,
            params={"response": "json", "stockNo": FIXED_STOCK, "date": FIXED_DATE},
        )

    def test_api_returns_ok_with_data(self):
        """確認 API 可達且回傳資料."""
        result = self._fetch()
        assert result.get("stat") == "OK"
        assert len(result.get("data", [])) > 0

    def test_date_field_is_roc_format(self):
        """tool 用 roc_to_ad(row[0]) 轉換，需確認日期含 /."""
        result = self._fetch()
        date_field = result["data"][0][0]
        assert "/" in date_field, f"日期格式異動！實際值: {date_field}"

    def test_price_fields_are_numeric(self):
        """tool 用 row[3]~row[6] 作為開高低收，需確認可轉數字."""
        result = self._fetch()
        row = result["data"][0]
        for idx in [3, 4, 5, 6]:
            val = row[idx].replace(",", "")
            try:
                float(val)
            except ValueError:
                pytest.fail(f"row[{idx}] 無法轉為數字，值為: {row[idx]}")


class TestBwibbuAllAPI:
    """全市場估值 - BWIBBU_ALL
    Tool get_market_valuation_by_date 使用 row[0]~row[4]:
    代號、名稱、本益比、殖利率、股價淨值比。
    """

    URL = "https://www.twse.com.tw/exchangeReport/BWIBBU_ALL"

    def _fetch(self):
        return TWSEAPIClient.get_json(
            self.URL,
            params={"response": "json", "date": FIXED_DATE},
        )

    def test_api_returns_ok_with_data(self):
        """確認 API 可達且回傳資料."""
        result = self._fetch()
        assert result.get("stat") == "OK"
        assert len(result.get("data", [])) > 0

    def test_row_has_stock_code_and_valuation_fields(self):
        """tool 用 row[0] 作為代號篩選，row[2]~row[4] 作為估值欄位."""
        result = self._fetch()
        first_row = result["data"][0]
        assert len(first_row) >= 5, f"欄位不足 5 個: {first_row}"


class TestMarginBalanceAPI:
    """融資融券 - MI_MARGN
    Tool get_margin_balance 使用 tables[1] 作為個股明細，
    用 row[0] 作為股票代號篩選。
    """

    URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"

    def _fetch(self):
        return TWSEAPIClient.get_json(
            self.URL,
            params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
        )

    def test_api_returns_ok_with_tables(self):
        """確認 API 可達且 tables[1] 含個股資料."""
        result = self._fetch()
        assert result.get("stat") == "OK"
        tables = result.get("tables", [])
        assert len(tables) >= 2, "MI_MARGN 應至少含 2 個 table"
        assert len(tables[1].get("data", [])) > 0


class TestStockDayAvgAPI:
    """個股月均價 - STOCK_DAY_AVG
    Tool get_stock_monthly_avg_history 使用 row[0] 作為日期（ROC 格式）。
    """

    URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG"

    def _fetch(self):
        return TWSEAPIClient.get_json(
            self.URL,
            params={"response": "json", "stockNo": FIXED_STOCK, "date": FIXED_DATE},
        )

    def test_api_returns_ok_with_data(self):
        """確認 API 可達且回傳資料."""
        result = self._fetch()
        assert result.get("stat") == "OK"
        assert len(result.get("data", [])) > 0
