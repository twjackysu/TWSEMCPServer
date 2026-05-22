"""Market statistics tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, MSG_NO_DATA, handle_api_errors, format_multiple_records

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market statistics tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(data_type="集中市場融資融券餘額")
    def get_margin_trading_info(limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場融資融券餘額。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/MI_MARGN")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場融資融券餘額")

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        result = f"共有 {total} 筆集中市場融資融券餘額資料"
        if total > limit or offset > 0:
            result += f"（顯示第 {offset + 1}–{end} 筆）"
        result += "：\n\n"
        result += format_multiple_records(page_data)

        remaining = total - offset - limit
        if remaining > 0:
            result += f"\n... 還有 {remaining} 筆，使用 offset={offset + limit} 查看更多"

        return result

    @mcp.tool
    @handle_api_errors(data_type="每5秒委託成交統計")
    def get_real_time_trading_stats(limit: int = 20) -> str:
        """查詢每5秒委託成交統計。

        回傳最新的5秒交易統計，包含累計買賣委託單數、委託量、成交筆數、成交量、成交值。

        Args:
            limit: 顯示最新幾筆（預設 20，從最新時間往回計算）
        """
        data = _client.fetch_data("/exchangeReport/MI_5MINS")
        if not data:
            return MSG_NO_DATA.format(data_type="每5秒委託成交統計")

        recent_data = data[-limit:] if len(data) > limit else data

        result = f"最新5秒委託成交統計 (共 {len(data)} 筆，顯示最新 {len(recent_data)} 筆):\n\n"

        for item in recent_data:
            time = item.get("Time", "N/A")
            acc_bid_orders = item.get("AccBidOrders", "N/A")
            acc_bid_volume = item.get("AccBidVolume", "N/A")
            acc_ask_orders = item.get("AccAskOrders", "N/A")
            acc_ask_volume = item.get("AccAskVolume", "N/A")
            acc_transaction = item.get("AccTransaction", "N/A")
            acc_trade_volume = item.get("AccTradeVolume", "N/A")
            acc_trade_value = item.get("AccTradeValue", "N/A")

            result += f"時間: {time}\n"
            result += f"  累計委買筆數: {acc_bid_orders}\n"
            result += f"  累計委買數量: {acc_bid_volume}\n"
            result += f"  累計委賣筆數: {acc_ask_orders}\n"
            result += f"  累計委賣數量: {acc_ask_volume}\n"
            result += f"  累計成交筆數: {acc_transaction}\n"
            result += f"  累計成交數量: {acc_trade_volume}\n"
            result += f"  累計成交金額(百萬): {acc_trade_value}\n"
            result += "\n"

        return result.strip()
