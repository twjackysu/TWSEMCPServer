"""TWSE history endpoints serve the latest trading day (or current month) when no date is sent.

The date-based tools in tools/history/ took over the OpenAPI "latest only" tools, so calling
them with no date must still work: they omit the ``date`` parameter and rely on upstream
answering with the latest data and echoing the date it served.
"""

import pytest

from tests.helpers import fetch_or_skip

TWSE = "https://www.twse.com.tw"

# (path, extra params, tool that depends on it)
LATEST_ENDPOINTS = [
    ("/rwd/zh/afterTrading/BWIBBU_d", {"selectType": "ALL"}, "get_stock_valuation_ratios"),
    ("/exchangeReport/MI_MARGN", {"selectType": "ALL"}, "get_margin_balance"),
    ("/rwd/zh/fund/MI_QFIIS", {"selectType": "ALLBUT0999"}, "get_foreign_holdings"),
    ("/rwd/zh/afterTrading/MI_INDEX", {"type": "ALLBUT0999"}, "get_stock_daily_trading"),
    ("/rwd/zh/TAIEX/MI_5MINS_HIST", {}, "get_taiex_index_history"),
    ("/rwd/zh/afterTrading/FMTQIK", {}, "get_market_turnover_history"),
    ("/exchangeReport/STOCK_DAY_AVG", {"stockNo": "2330"}, "get_stock_monthly_average"),
    ("/rwd/zh/afterTrading/FMSRFK", {"stockNo": "2330"}, "get_stock_monthly_trading"),
]


@pytest.mark.parametrize("path,params,tool", LATEST_ENDPOINTS, ids=[t for _p, _x, t in LATEST_ENDPOINTS])
def test_omitting_date_returns_latest_data(path, params, tool):
    resp = fetch_or_skip(f"{TWSE}{path}", params={"response": "json", **params})
    assert resp.get("stat") == "OK", f"{tool}: 不帶 date 時上游不再回資料（stat={resp.get('stat')}）"
    served = str(resp.get("date") or "")
    assert len(served) == 8 and served.isdigit(), f"{tool}: 不帶 date 時不再回傳實際資料日期: {served!r}"
    rows = resp.get("data") or [r for t in resp.get("tables") or [] for r in (t.get("data") or [])]
    assert rows, f"{tool}: 不帶 date 時回應沒有任何資料列"
