"""Periodic trading data tools (monthly, yearly)."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register periodic trading tools with the MCP instance."""
    
    @mcp.tool
    def get_stock_monthly_average(code: str) -> str:
        """Obtain daily closing price and monthly average price for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/STOCK_DAY_AVG_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_stock_monthly_trading(code: str) -> str:
        """Obtain monthly trading information for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/FMSRFK_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_stock_yearly_trading(code: str) -> str:
        """Obtain yearly trading information for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/FMNPTK_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""