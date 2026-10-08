"""Offline test double for TWSEAPIClient（不打網路）。

只替換最底層的 ``_request``，``fetch_data`` / ``fetch_company_data`` /
``fetch_json`` / ``fetch_bytes`` 仍走真實程式碼，因此篩選、快取等 client 端邏輯
照常被執行。未設定路由的 URL 會直接拋錯，避免測試不小心連上真實 API。
"""

import json
from typing import Any, Callable, Dict, Union

from utils.api_client import TWSEAPIClient

# 路由值可以是固定 payload，或依 (params, body) 動態回傳 payload 的函式；
# body 是表單 data 或 JSON body（MOPS 新版 API）。
# payload 為 bytes 時當作 response body（fetch_bytes），其餘當作已解析的 JSON。
Payload = Union[bytes, Any]
Route = Union[Payload, Callable[[Dict[str, Any], Dict[str, Any]], Payload]]


class _CannedResponse:
    def __init__(self, payload: Payload):
        self._payload = payload
        # JSON payload 也提供 content，讓走快取（bytes 再 json.loads）的路徑同樣可用
        self.content = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def json(self):
        return self._payload


class OfflineClient(TWSEAPIClient):
    """``routes`` 以 URL 結尾比對：可填完整 URL，或 OpenAPI 的 endpoint（如 ``/opendata/t187ap37_L``）."""

    def __init__(self, routes: Dict[str, Route]):
        super().__init__(request_interval=0, cache_ttl=0)
        self.routes = routes

    def _request(self, url, params=None, headers=None, timeout=None, method="GET", data=None, json_body=None,
                 session=None):
        for suffix, route in self.routes.items():
            if url.endswith(suffix):
                # 動態路由的第二個參數是 request body：表單（data）或 JSON（json_body）
                body = data if data is not None else json_body
                payload = route(params or {}, body or {}) if callable(route) else route
                return _CannedResponse(payload)
        raise AssertionError(f"OfflineClient 沒有設定此 URL 的路由: {url}")
