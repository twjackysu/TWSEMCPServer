"""測試 openapi.taifex.com.tw 期交所 API。只驗證 tool 寫死的欄位。"""

from tests.helpers import fetch_or_skip

# TAIFEX requires browser-like User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fetch(endpoint: str) -> list:
    return fetch_or_skip(
        f"https://openapi.taifex.com.tw/v1/{endpoint}",
        headers=HEADERS, timeout=15,
    )


class TestFuturesInstitutionalAPI:
    """Tool get_futures_institutional 用 Date, Item 做顯示，
    用 FuturesTradingVolume(Long/Short/Net), FuturesOI(Long/Short/Net) 做數據。
    """

    def test_api_returns_data_with_key_fields(self):
        data = _fetch("MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate")
        assert isinstance(data, list) and len(data) > 0
        assert "Date" in data[0]
        assert "Item" in data[0]


class TestPutCallRatioAPI:
    """Tool get_put_call_ratio 用 Date, PutVolume, CallVolume, PutCallVolumeRatio% 做顯示。"""

    def test_api_returns_data_with_key_fields(self):
        data = _fetch("PutCallRatio")
        assert isinstance(data, list) and len(data) > 0
        assert "Date" in data[0]
        assert "PutCallVolumeRatio%" in data[0]


def test_openapi_still_serves_json_for_some_endpoint():
    """守門測試：CSV 退化必須維持「間歇且分端點」，不能是全站永久改格式。

    fetch_or_skip 會把 openapi.taifex.com.tw 回 CSV 當成暫時性雜訊而 skip（見
    tests/helpers.py 的 _is_taifex_csv_fallback）。那個豁免的前提是：同一時間只有
    部分端點退化成 CSV，其餘仍供 JSON。若某天整站永久改成 CSV，上面每個測試都會
    變成 skip 而 CI 恆綠——這支測試就是為了讓那種情況照樣紅。
    """
    import json as _json
    import requests as _requests

    probes = [
        "PutCallRatio",
        "va01",
        "DailyMarketReportFut",
        "OpenInterestOfLargeTradersFutures",
        "MarketDataOfMajorInstitutionalTradersGeneralBytheDate",
    ]
    served_json, reached = [], 0
    for endpoint in probes:
        try:
            resp = _requests.get(
                f"https://openapi.taifex.com.tw/v1/{endpoint}",
                headers=HEADERS, timeout=15, verify=False,
            )
            resp.encoding = "utf-8"
        except _requests.RequestException:
            continue
        reached += 1
        try:
            _json.loads(resp.text.lstrip("\ufeff"))
            served_json.append(endpoint)
        except ValueError:
            pass

    if reached == 0:
        import pytest as _pytest
        _pytest.skip("無法連線至 openapi.taifex.com.tw")

    assert served_json, (
        f"探測的 {reached} 個端點全部回傳 CSV，openapi.taifex.com.tw 可能已永久"
        f"改為 CSV。請改寫 tools/taifex/ 的解析並移除 helpers.py 的 CSV 豁免。"
    )
