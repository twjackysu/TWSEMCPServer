"""Stock valuation tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register valuation tools with the MCP instance."""
    
    @mcp.tool
    def get_stock_valuation_ratios(code: str) -> str:
        """Obtain P/E ratio, dividend yield, and P/B ratio for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/BWIBBU_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""