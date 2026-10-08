"""openapi.taifex.com.tw 的全站格式守門測試。

個別端點的欄位測試在 test_taifex_new_api.py / test_taifex_batch2_api.py；已改用下載頁的工具
見 test_taifex_history_api.py。
"""


# TAIFEX requires browser-like User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def test_openapi_still_serves_json_for_some_endpoint():
    """守門測試：CSV 退化必須維持「間歇且分端點」，不能是全站永久改格式。

    fetch_or_skip 會把 openapi.taifex.com.tw 回 CSV 當成暫時性雜訊而 skip（見
    tests/helpers.py 的 _is_taifex_csv_fallback）。那個豁免的前提是：同一時間只有
    部分端點退化成 CSV，其餘仍供 JSON。若某天整站永久改成 CSV，上面每個測試都會
    變成 skip 而 CI 恆綠——這支測試就是為了讓那種情況照樣紅。
    """
    import json as _json
    import requests as _requests

    # 仍由 openapi 提供資料的端點（其餘 TAIFEX 工具已改用 www.taifex.com.tw 下載頁）
    probes = [
        "va01",
        "DailyOptionsDelta",
        "IndexFuturesAndOptionsMargining",
        "AnnualTradingVolume",
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
