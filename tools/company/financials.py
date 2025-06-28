"""Company financial statements tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register company financials tools with the MCP instance."""
    
    @mcp.tool
    def get_company_income_statement(code: str) -> str:
        """Obtain comprehensive income statement for a listed company based on its stock code (general industry)."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap06_L_ci", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_balance_sheet(code: str) -> str:
        """Obtain balance sheet for a listed company based on its stock code (general industry)."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap07_L_ci", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""