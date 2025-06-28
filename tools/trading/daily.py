"""Daily trading data tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register daily trading tools with the MCP instance."""
    
    @mcp.tool
    def get_stock_daily_trading(code: str) -> str:
        """Obtain daily trading information for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/STOCK_DAY_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""