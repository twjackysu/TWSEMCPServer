"""Company ESG and governance tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register company ESG tools with the MCP instance."""
    
    @mcp.tool
    def get_company_governance_info(code: str) -> str:
        """Obtain corporate governance information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_9", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_climate_management(code: str) -> str:
        """Obtain climate-related management information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_8", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_risk_management(code: str) -> str:
        """Obtain risk management policy information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_19", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_supply_chain_management(code: str) -> str:
        """Obtain supply chain management information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_13", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_info_security(code: str) -> str:
        """Obtain information security data for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_16", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""