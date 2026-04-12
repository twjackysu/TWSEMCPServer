"""TAIFEX institutional futures position data."""

import requests
import logging
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.config import APIConfig

logger = logging.getLogger(__name__)

TAIFEX_URL = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDividedByFuturesAndOptionsBytheDate"

# TAIFEX requires browser-like User-Agent
TAIFEX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fetch_taifex(url: str) -> list:
    """Fetch data from TAIFEX API with browser-like headers."""
    resp = requests.get(url, headers=TAIFEX_HEADERS, verify=False, timeout=APIConfig.DEFAULT_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    data = resp.json()
    return data if isinstance(data, list) else []


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX futures position tools."""

    @mcp.tool
    @handle_api_errors()
    def get_futures_institutional() -> str:
        """查詢三大法人期貨與選擇權每日交易資訊，為判斷市場方向的重要指標。
        外資期貨淨部位為台股最常被引用的籌碼指標之一。

        Returns:
            三大法人（外資、投信、自營商）的期貨與選擇權多空部位、交易量與未平倉資訊
        """
        data = _fetch_taifex(TAIFEX_URL)

        if not data:
            return "查無三大法人期貨部位資料"

        lines = ["【三大法人期貨與選擇權交易資訊】\n"]

        for item in data:
            date = item.get("Date", "?")
            investor = item.get("Item", "?")
            ft_long = item.get("FuturesTradingVolume(Long)", "-")
            ft_short = item.get("FuturesTradingVolume(Short)", "-")
            ft_net = item.get("FuturesTradingVolume(Net)", "-")
            oi_long = item.get("FuturesOI(Long)", "-")
            oi_short = item.get("FuturesOI(Short)", "-")
            oi_net = item.get("FuturesOI(Net)", "-")

            lines.append(
                f"[{date}] {investor}\n"
                f"  期貨交易: 多 {ft_long} / 空 {ft_short} / 淨 {ft_net}\n"
                f"  期貨未平倉: 多 {oi_long} / 空 {oi_short} / 淨 {oi_net}"
            )

        return "\n".join(lines)
