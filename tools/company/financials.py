"""Company financial statements tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register company financials tools with the MCP instance."""
    
    def _get_industry_api_suffix(code: str) -> str:
        """Get the appropriate API suffix based on company industry."""
        try:
            # Get company profile to determine industry
            profile_data = TWSEAPIClient.get_company_data("/opendata/t187ap03_L", code)
            if not profile_data:
                return "_ci"  # Default to general industry
            
            industry = profile_data.get("產業別", "")
            
            # Map industry to API suffix
            industry_mapping = {
                "金融業": "_basi",
                "證券期貨業": "_bd", 
                "金控業": "_fh",
                "保險業": "_ins",
                "異業": "_mim",
                "一般業": "_ci"
            }
            
            # Check if industry exactly matches or contains any of the key terms
            for industry_key, suffix in industry_mapping.items():
                if industry_key in industry or industry == industry_key:
                    return suffix
            
            return "_ci"  # Default to general industry if no match
        except Exception:
            return "_ci"  # Default to general industry on error
    
    @mcp.tool
    def get_company_income_statement(code: str) -> str:
        """Obtain comprehensive income statement for a listed company based on its stock code. 
        Automatically detects company industry and uses appropriate financial statement format:
        - General industry (一般業)
        - Financial services (金融業) 
        - Securities & futures (證券期貨業)
        - Financial holding companies (金控業)
        - Insurance (保險業)
        - Other industries (異業)
        """
        try:
            suffix = _get_industry_api_suffix(code)
            endpoint = f"/opendata/t187ap06_L{suffix}"
            data = TWSEAPIClient.get_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_balance_sheet(code: str) -> str:
        """Obtain balance sheet for a listed company based on its stock code.
        Automatically detects company industry and uses appropriate financial statement format:
        - General industry (一般業)
        - Financial services (金融業)
        - Securities & futures (證券期貨業) 
        - Financial holding companies (金控業)
        - Insurance (保險業)
        - Other industries (異業)
        """
        try:
            suffix = _get_industry_api_suffix(code)
            endpoint = f"/opendata/t187ap07_L{suffix}"
            data = TWSEAPIClient.get_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""