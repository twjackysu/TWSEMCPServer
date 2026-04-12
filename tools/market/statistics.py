"""Market statistics tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records, MSG_QUERY_FAILED

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market statistics tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    def get_margin_trading_info() -> str:
        """查詢集中市場融資融券餘額。"""
        try:
            data = _client.fetch_data("/exchangeReport/MI_MARGN")
            # 只取前10筆避免資料過多
            return format_multiple_records(data[:10] if data else [])
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_real_time_trading_stats() -> str:
        """查詢每5秒委託成交統計。

        回傳最新的5秒交易統計，包含累計買賣委託單數、委託量、成交筆數、成交量、成交值。
        """
        try:
            data = _client.fetch_data("/exchangeReport/MI_5MINS")
            if not data:
                return "無5秒委託成交統計資料"
            
            # 只取最新的20筆避免資料過多
            recent_data = data[-20:] if len(data) > 20 else data
            
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
        except Exception as e:
            return f"取得5秒委託成交統計時發生錯誤: {str(e)}"