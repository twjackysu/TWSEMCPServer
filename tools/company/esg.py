"""Company ESG and governance tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline, has_meaningful_data

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
                has_meaningful_data(item, "因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)")
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

    @mcp.tool
    def get_company_inclusive_finance(code: str) -> str:
        """Obtain inclusive finance information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_17", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_companies_with_inclusive_finance_data() -> str:
        """Get all listed companies that have reported inclusive finance activities (excluding zero or N/A values)."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap46_L_17")
            # Filter companies with meaningful data in any of the three fields
            filtered_data = [
                item for item in data
                if isinstance(item, dict) and
                has_meaningful_data(item, [
                    "對促進小型企業及社區發展的貸放件數(件)",
                    "對促進小型企業及社區發展的貸放餘額(仟元)",
                    "對缺少銀行服務之弱勢族群提供金融教育之參與人數(人)"
                ])
            ]

            if not filtered_data:
                return "目前沒有公司報告普惠金融相關數據。"

            # Format the output
            result = f"共有 {len(filtered_data)} 家公司報告普惠金融相關數據：\n\n"
            for item in filtered_data:
                company_code = item.get("公司代號", "N/A")
                company_name = item.get("公司名稱", "N/A")
                loan_count = item.get("對促進小型企業及社區發展的貸放件數(件)", "N/A")
                loan_amount = item.get("對促進小型企業及社區發展的貸放餘額(仟元)", "N/A")
                education_count = item.get("對缺少銀行服務之弱勢族群提供金融教育之參與人數(人)", "N/A")
                report_year = item.get("報告年度", "N/A")

                result += f"- {company_name} ({company_code}) [報告年度: {report_year}]\n"
                result += f"  貸放件數: {loan_count} 件\n"
                result += f"  貸放餘額: {loan_amount} 千元\n"
                result += f"  金融教育參與人數: {education_count} 人\n\n"

            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_company_community_relations(code: str) -> str:
        """Obtain community relations information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_15", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_companies_with_refineries_in_populated_areas() -> str:
        """Get all listed companies that have reported refineries in populated areas (excluding zero or N/A values)."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap46_L_15")
            # Filter companies with meaningful data (non-zero and non-N/A refinery count)
            filtered_data = [
                item for item in data
                if isinstance(item, dict) and
                has_meaningful_data(item, "在人口密集地區的煉油廠數量(座)")
            ]

            if not filtered_data:
                return "目前沒有公司報告在人口密集地區設有煉油廠。"

            # Format the output
            result = f"共有 {len(filtered_data)} 家公司報告在人口密集地區設有煉油廠：\n\n"
            for item in filtered_data:
                company_code = item.get("公司代號", "N/A")
                company_name = item.get("公司名稱", "N/A")
                refinery_count = item.get("在人口密集地區的煉油廠數量(座)", "N/A")
                report_year = item.get("報告年度", "N/A")
                result += f"- {company_name} ({company_code}): {refinery_count} 座 (報告年度: {report_year})\n"

            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_company_ownership_and_control(code: str) -> str:
        """Obtain ownership and control information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_18", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_product_quality_safety(code: str) -> str:
        """Obtain product quality and safety information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_14", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_food_safety(code: str) -> str:
        """Obtain food safety information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_12", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_product_lifecycle(code: str) -> str:
        """Obtain product lifecycle information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_11", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_fuel_management(code: str) -> str:
        """Obtain fuel management information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_10", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_investor_communications(code: str) -> str:
        """Obtain investor communications information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_7", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_board_info(code: str) -> str:
        """Obtain board information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_6", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_human_development(code: str) -> str:
        """Obtain human development information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_5", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_waste_management(code: str) -> str:
        """Obtain waste management information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_4", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_water_management(code: str) -> str:
        """Obtain water resource management information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_3", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_energy_management(code: str) -> str:
        """Obtain energy management information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_2", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_greenhouse_gas_emissions(code: str) -> str:
        """Obtain greenhouse gas emissions information for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap46_L_1", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""