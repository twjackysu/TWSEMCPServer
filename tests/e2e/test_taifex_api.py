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
