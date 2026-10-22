"""
測試 twse.com.tw/exchangeReport 歷史行情 API。
只驗證 tools 中有寫死用到的欄位索引與格式，足以偵測來源 API 結構異動。
"""

from sources.twse.bwibbu_d import valuation_ratios
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
        assert month.name == "台積電", f"title 格式異動（名稱取自 title）？{month.title!r}"
        assert month.rows and all(r.day.year == 2025 and r.day.month == 1 for r in month.rows), "date 不再對應該月"
        first = month.rows[0]
        assert None not in (first.open, first.high, first.low, first.close, first.volume), f"數字格式已變更：{first}"

    def test_unknown_code_is_no_data_not_an_error(self):
        assert gateway_or_skip(stock_day_month, "9999", 2025, 1) is None


class TestBwibbuDailyGateway:
    """全市場估值 - BWIBBU_d（sources/twse/bwibbu_d.py）
    get_stock_valuation_ratios 與 services/market_snapshot 都只透過這個 gateway 讀 BWIBBU_d；欄位改名時
    gateway 丟 UpstreamFormatError。tool 靠回應的 date 擋掉「拿到別天資料卻標成所查日期」。
    """

    def test_fixed_day_parses_and_echoes_its_date(self):
        report = gateway_or_skip(valuation_ratios, FIXED_DATE)
        assert report.found and report.date == FIXED_DATE, f"回應日期 {report.date!r} 與所查日期 {FIXED_DATE} 不符"
        tsmc = next((v for v in report.valuations if v.code == FIXED_STOCK), None)
        assert tsmc is not None and tsmc.name == "台積電", f"{FIXED_DATE} 估值找不到 {FIXED_STOCK}"
        assert None not in (tsmc.close, tsmc.dividend_yield, tsmc.pe, tsmc.pb), f"數字格式已變更：{tsmc}"

    def test_endpoint_actually_honours_date(self):
        """兩個不同日期必須回傳不同資料——舊的 BWIBBU_ALL 端點就是敗在這裡."""
        other_date = "20240315"
        other = gateway_or_skip(valuation_ratios, other_date)
        assert other.date == other_date
        assert other.valuations[0] != gateway_or_skip(valuation_ratios, FIXED_DATE).valuations[0], (
            "不同日期回傳相同資料，端點已不再支援歷史查詢"
        )


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
