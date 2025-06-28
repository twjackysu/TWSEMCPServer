"""Market indices tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline, format_multiple_records

def register_tools(mcp):
    """Register market indices tools with the MCP instance."""
    
    @mcp.tool
    def get_market_index_info() -> str:
        """Obtain daily market closing information and overall market statistics."""
        try:
            data = TWSEAPIClient.get_latest_market_data("/exchangeReport/MI_INDEX", count=1)
            return format_properties_with_values_multiline(data[0]) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_market_historical_index() -> str:
        """Obtain historical TAIEX (Taiwan Capitalization Weighted Stock Index) data for long-term trend analysis."""
        try:
            data = TWSEAPIClient.get_latest_market_data("/indicesReport/MI_5MINS_HIST", count=20)
            return format_multiple_records(data)
        except Exception:
            return ""