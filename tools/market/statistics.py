"""Market statistics tools."""

from utils import TWSEAPIClient, format_multiple_records

def register_tools(mcp):
    """Register market statistics tools with the MCP instance."""
    
    @mcp.tool
    def get_margin_trading_info() -> str:
        """Obtain margin trading and short selling balance information for the market."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/MI_MARGN")
            # 只取前10筆避免資料過多
            return format_multiple_records(data[:10] if data else [])
        except Exception:
            return ""

    @mcp.tool
    def get_real_time_trading_stats() -> str:
        """Obtain real-time 5-second trading statistics including order volumes and transaction counts."""
        try:
            data = TWSEAPIClient.get_latest_market_data("/exchangeReport/MI_5MINS", count=10)
            return format_multiple_records(data)
        except Exception:
            return ""