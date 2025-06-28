"""Company basic information tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register company basic info tools with the MCP instance."""
    
    @mcp.tool
    def get_company_profile(code: str) -> str:
        """Obtain the basic information of a listed company as a JSON string object based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap03_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_dividend(code: str) -> str:
        """Obtain the dividend distribution information of a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap45_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_monthly_revenue(code: str) -> str:
        """Obtain monthly revenue information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap05_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""