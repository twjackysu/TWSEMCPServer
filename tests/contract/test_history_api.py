"""
測試 twse.com.tw/exchangeReport 歷史行情 API。
只驗證 tools 中有寫死用到的欄位索引與格式，足以偵測來源 API 結構異動。
"""

import pytest
from sources.twse.stock_day import stock_day_month
from tests.helpers import fetch_or_skip, gateway_or_skip

# Use a fixed historical trading day to ensure data stability
FIXED_DATE = "20250103"
FIXED_STOCK = "2330"  # TSMC


class TestStockDayGateway:
    """個股歷史日K - STOCK_DAY（sources/twse/stock_day.py）
    get_stock_history 與 services/price_series 都只透過這個 gateway 讀 STOCK_DAY；真實回應要能建出
    StockDayMonth。欄位改名、搬走時 gateway 會丟 UpstreamFormatError，這裡就會失敗。
    """

    def test_fixed_month_parses_into_typed_rows(self):
        month = gateway_or_skip(stock_day_month, FIXED_STOCK, 2025, 1)
        assert month is not None, f"{FIXED_STOCK} 2025-01 應有交易資料"
        assert month.name == "台積電", f"title 格式異動？{month.title!r}"
        assert month.rows and all(r.day.year == 2025 and r.day.month == 1 for r in month.rows)
        for r in month.rows:  # 2330 每個交易日都有成交
            assert None not in (r.open, r.high, r.low, r.close, r.volume, r.value, r.transactions), r
            assert r.low <= r.open <= r.high and r.low <= r.close <= r.high, r
            assert r.change.strip()[:1] in ("+", "-", "0", "X"), f"漲跌價差格式異動：{r.change!r}"

    def test_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(stock_day_month, "9999", 2025, 1) is None


@pytest.fixture(scope="class")
def bwibbu_d_data():
    return fetch_or_skip(
        "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d",
        params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
    )


class TestBwibbuDailyAPI:
    """全市場估值 - BWIBBU_d
    Tool get_stock_valuation_ratios 依 COL_* 常數取用欄位，
    並以回應的 date 欄位確認拿到的確實是所查日期的資料。
    """

    def test_field_order_matches_column_constants(self, bwibbu_d_data):
        """tool 寫死欄位索引，需確認 fields 順序未變."""
        assert bwibbu_d_data.get("stat") == "OK"
        fields = bwibbu_d_data["fields"]
        expected = [
            "證券代號", "證券名稱", "收盤價", "殖利率(%)",
            "股利年度", "本益比", "股價淨值比", "財報年/季",
        ]
        assert fields == expected, f"欄位順序異動！實際值: {fields}"

    def test_response_echoes_requested_date(self, bwibbu_d_data):
        """tool 靠 date 欄位擋掉「拿到別天資料卻標成所查日期」."""
        assert bwibbu_d_data.get("date") == FIXED_DATE, (
            f"回應日期 {bwibbu_d_data.get('date')} 與所查日期 {FIXED_DATE} 不符"
        )

    def test_endpoint_actually_honours_date(self):
        """兩個不同日期必須回傳不同資料——舊的 BWIBBU_ALL 端點就是敗在這裡."""
        other_date = "20240315"
        other = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d",
            params={"response": "json", "date": other_date, "selectType": "ALL"},
        )
        assert other.get("date") == other_date
        assert other["data"][0] != _first_row_for(FIXED_DATE), (
            "不同日期回傳相同資料，端點已不再支援歷史查詢"
        )


def _first_row_for(date: str):
    resp = fetch_or_skip(
        "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d",
        params={"response": "json", "date": date, "selectType": "ALL"},
    )
    return resp["data"][0]


class TestMarginBalanceAPI:
    """融資融券 - MI_MARGN
    Tool get_margin_balance 使用 tables[1] 作為個股明細，row[0] 作為股票代號篩選。
    """

    def test_tables_structure(self):
        """tables[1] 需存在且含資料列."""
        result = fetch_or_skip(
            "https://www.twse.com.tw/exchangeReport/MI_MARGN",
            params={"response": "json", "date": FIXED_DATE, "selectType": "ALL"},
        )
        assert result.get("stat") == "OK"
        tables = result.get("tables", [])
        assert len(tables) >= 2, "MI_MARGN 應至少含 2 個 table，tables[1] 為個股明細"
        assert len(tables[1].get("data", [])) > 0


class TestStockDayAvgAPI:
    """個股月均價 - STOCK_DAY_AVG
    Tool get_stock_monthly_average 使用 row[0] 作為日期（需含 /），row[1] 作為均價。
    """

    def test_row_structure(self):
        """row[0] 需含 / (ROC 日期格式)，row[1] 為均價。"""
        result = fetch_or_skip(
            "https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG",
            params={"response": "json", "stockNo": FIXED_STOCK, "date": FIXED_DATE},
        )
        assert result.get("stat") == "OK"
        data = result.get("data", [])
        assert len(data) > 0
        # find first row with date (last row may be summary without /)
        date_rows = [r for r in data if "/" in r[0]]
        assert date_rows, "找不到含 / 的日期列，row[0] 日期格式可能已變更"
        assert len(date_rows[0]) >= 2, "row[1] 均價欄位不存在，欄位數不足"
