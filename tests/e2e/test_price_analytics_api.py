"""Contract tests for the sources behind the price analytics tools (utils/price_series.py):
get_adjusted_price_history, get_technical_indicators and get_otc_exright.

STOCK_DAY / tradingStock row layouts and TWT49U columns are pinned elsewhere
(test_history_api.py, test_otc_history_api.py, test_history_tier3_api.py); these tests pin
the extra behaviour the analytics rely on.
"""

from tests.helpers import fetch_or_skip
from utils.price_series import STOCK_DAY_URL, TPEX_EXRIGHT_URL

FIXED_MONTH = "20250101"


def test_listed_endpoint_rejects_otc_codes():
    """市場判斷：先查上市 STOCK_DAY，查無資料（stat 非 OK）才改查上櫃."""
    resp = fetch_or_skip(STOCK_DAY_URL, params={"response": "json", "stockNo": "6488", "date": FIXED_MONTH})
    assert resp.get("stat") != "OK" and not resp.get("data"), f"STOCK_DAY 開始接受上櫃代號: {resp!r:.200}"


def test_stock_day_title_carries_code_and_name():
    """股票名稱取自 title 的第三段：'114年01月 2330 台積電 各日成交資訊'."""
    resp = fetch_or_skip(STOCK_DAY_URL, params={"response": "json", "stockNo": "2330", "date": FIXED_MONTH})
    parts = str(resp.get("title", "")).split()
    assert len(parts) >= 3 and parts[1] == "2330" and parts[2] == "台積電", f"title 格式已變更: {resp.get('title')}"


def test_otc_exright_results_columns_and_range():
    """get_otc_exright 與上櫃還原權息使用 row[0]~row[16]；區間查詢需支援跨年."""
    resp = fetch_or_skip(
        TPEX_EXRIGHT_URL, params={"startDate": "2025/01/01", "endDate": "2025/12/31", "response": "json"}
    )
    table = (resp.get("tables") or [{}])[0]
    assert table.get("fields", [])[:17] == [
        "除權息日期", "代號", "名稱", "除權息前收盤價", "除權息參考價", "權值", "息值", "權值+息值", "權/息",
        "漲停價", "跌停價", "開始交易基準價", "減除股利參考價", "現金股利", "每仟股無償配股", "現金增資股數", "現金增資認購價",
    ], f"欄位已變更: {table.get('fields')}"
    rows = table.get("data") or []
    assert len(rows) > 500, f"整年區間筆數異常（{len(rows)}），區間查詢可能被限制"


def test_otc_exright_without_dates_returns_today_onward():
    resp = fetch_or_skip(TPEX_EXRIGHT_URL, params={"response": "json"})
    assert "~" in str(resp.get("date", "")), f"不帶日期時不再回傳今天起的區間: {resp.get('date')!r}"
