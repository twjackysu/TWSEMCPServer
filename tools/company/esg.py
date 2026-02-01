"""Company ESG and governance tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline, has_meaningful_data
from utils.tool_factory import create_company_tool

# Simple company data tools: (endpoint, name, docstring)
SIMPLE_ESG_TOOLS = [
    ("/opendata/t187ap46_L_9", "get_company_governance_info",
     "Obtain corporate governance information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_8", "get_company_climate_management",
     "Obtain climate-related management information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_19", "get_company_risk_management",
     "Obtain risk management policy information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_13", "get_company_supply_chain_management",
     "Obtain supply chain management information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_16", "get_company_info_security",
     "Obtain information security data for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_20", "get_company_anticompetitive_litigation",
     "Obtain anti-competitive litigation losses information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_17", "get_company_inclusive_finance",
     "Obtain inclusive finance information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_15", "get_company_community_relations",
     "Obtain community relations information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_18", "get_company_ownership_and_control",
     "Obtain ownership and control information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_14", "get_company_product_quality_safety",
     "Obtain product quality and safety information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_12", "get_company_food_safety",
     "Obtain food safety information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_11", "get_company_product_lifecycle",
     "Obtain product lifecycle information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_10", "get_company_fuel_management",
     "Obtain fuel management information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_7", "get_company_investor_communications",
     "Obtain investor communications information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_6", "get_company_board_info",
     "Obtain board information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_5", "get_company_human_development",
     "Obtain human development information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_4", "get_company_waste_management",
     "Obtain waste management information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_3", "get_company_water_management",
     "Obtain water resource management information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_2", "get_company_energy_management",
     "Obtain energy management information for a listed company based on its stock code."),
    ("/opendata/t187ap46_L_1", "get_company_greenhouse_gas_emissions",
     "Obtain greenhouse gas emissions information for a listed company based on its stock code."),
]


def register_tools(mcp):
    """Register company ESG tools with the MCP instance."""
    
    # Register simple tools via factory
    for endpoint, name, doc in SIMPLE_ESG_TOOLS:
        create_company_tool(mcp, endpoint, name, doc)
    
    # Complex tools with custom logic below
    
    @mcp.tool
    def get_companies_with_anticompetitive_losses() -> str:
        """Get all listed companies that have reported monetary losses from anti-competitive litigation (excluding zero or N/A values)."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap46_L_20")
            filtered_data = [
                item for item in data 
                if isinstance(item, dict) and 
                has_meaningful_data(item, "因與反競爭行為條例相關的法律訴訟而造成的金錢損失總額(仟元)")
            ]
            
            if not filtered_data:
                return "目前沒有公司報告反競爭行為法律訴訟的金錢損失。"
            
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
    def get_companies_with_inclusive_finance_data() -> str:
        """Get all listed companies that have reported inclusive finance activities (excluding zero or N/A values)."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap46_L_17")
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
    def get_companies_with_refineries_in_populated_areas() -> str:
        """Get all listed companies that have reported refineries in populated areas (excluding zero or N/A values)."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap46_L_15")
            filtered_data = [
                item for item in data
                if isinstance(item, dict) and
                has_meaningful_data(item, "在人口密集地區的煉油廠數量(座)")
            ]

            if not filtered_data:
                return "目前沒有公司報告在人口密集地區設有煉油廠。"

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
