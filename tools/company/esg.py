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

    @mcp.tool
    def get_company_anticompetitive_litigation(code: str) -> str:
        """Obtain anti-competitive litigation losses information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_20", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_companies_with_anticompetitive_losses() -> str:
        """Get all listed companies that have reported monetary losses from anti-competitive litigation (excluding zero or N/A values)."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap46_L_20")
            # Filter companies with actual losses (non-zero and non-N/A)
            filtered_data = [
                item for item in data 
                if isinstance(item, dict) and 
                item.get("因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)") not in ["0.000", "0", "N/A", "", None]
            ]
            
            if not filtered_data:
                return "目前沒有公司報告反競爭行為法律訴訟的金錢損失。"
            
            # Format the output
            result = f"共有 {len(filtered_data)} 家公司報告反競爭行為法律訴訟的金錢損失：\n\n"
            for item in filtered_data:
                company_code = item.get("公司代號", "N/A")
                company_name = item.get("公司名稱", "N/A")
                loss_amount = item.get("因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)", "N/A")
                report_year = item.get("報告年度", "N/A")
                result += f"- {company_name} ({company_code}): {loss_amount} 千元 (報告年度: {report_year})\n"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"