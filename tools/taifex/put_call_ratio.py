"""TAIFEX Put/Call Ratio data."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

TAIFEX_PCR_URL = "https://openapi.taifex.com.tw/v1/PutCallRatio"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX put/call ratio tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_put_call_ratio() -> str:
        """查詢台指選擇權 Put/Call Ratio，為衡量市場恐慌與樂觀程度的情緒指標。
        PCR > 1.5 通常視為過度悲觀，< 0.5 通常視為過度樂觀。

        Returns:
            近期每日的成交量 PCR、未平倉量 PCR，以及 put/call 各自的成交量與未平倉量
        """
        data = _client.fetch_json(TAIFEX_PCR_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無 Put/Call Ratio 資料"

        lines = [f"【台指選擇權 Put/Call Ratio】（近 {len(data)} 個交易日）\n"]

        for item in data:
            date = item.get("Date", "?")
            put_vol = item.get("PutVolume", "-")
            call_vol = item.get("CallVolume", "-")
            pcr_vol = item.get("PutCallVolumeRatio%", "-")
            put_oi = item.get("PutOI", "-")
            call_oi = item.get("CallOI", "-")
            pcr_oi = item.get("PutCallOIRatio%", "-")

            lines.append(
                f"{date} | 成交量 PCR: {pcr_vol}% (Put:{put_vol} Call:{call_vol}) | "
                f"未平倉 PCR: {pcr_oi}% (Put:{put_oi} Call:{call_oi})"
            )

        return "\n".join(lines)
