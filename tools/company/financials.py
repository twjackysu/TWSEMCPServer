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

    @mcp.tool
    def get_company_quarterly_earnings_forecast_achievement(code: str) -> str:
        """Obtain quarterly earnings forecast achievement (simplified) for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap15_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_quarterly_audit_variance(code: str) -> str:
        """Obtain quarterly comprehensive income audited/reviewed figures that differ from forecast by more than 10% for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap16_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_profitability_analysis(code: str) -> str:
        """Get profitability analysis for a specific listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap17_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_company_profitability_analysis_summary(
        page_size: int = 20, 
        page_number: int = 1,
        order_by: str = "稅後純益率(%)(稅後純益)/(營業收入)",
        order_direction: str = "desc"
    ) -> str:
        """Get profitability analysis query summary table (all companies aggregate report).
        
        Args:
            page_size: Number of records per page (default: 20, max: 100)
            page_number: Page number to retrieve (default: 1, starts from 1)
            order_by: Field name to sort by. Available fields:
                - "公司代號" (Company Code)
                - "公司名稱" (Company Name)
                - "營業收入(百萬元)" (Revenue in millions)
                - "毛利率(%)(營業毛利)/(營業收入)" (Gross Margin %)
                - "營業利益率(%)(營業利益)/(營業收入)" (Operating Margin %)
                - "稅前純益率(%)(稅前純益)/(營業收入)" (Pre-tax Margin %)
                - "稅後純益率(%)(稅後純益)/(營業收入)" (Net Margin %)
                - "年度" (Year)
                - "季別" (Quarter)
            order_direction: Sort direction, "asc" for ascending or "desc" for descending (default: "asc")
        """
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap17_L")
            if not data:
                return "目前沒有營益分析查詢彙總表資料。"
            
            # Validate and adjust parameters
            page_size = min(max(1, page_size), 100)  # Between 1 and 100
            page_number = max(1, page_number)  # At least 1
            order_direction = order_direction.lower()
            if order_direction not in ["asc", "desc"]:
                order_direction = "asc"
            
            # Valid sortable fields
            valid_fields = [
                "公司代號", "公司名稱", "年度", "季別",
                "營業收入(百萬元)", 
                "毛利率(%)(營業毛利)/(營業收入)",
                "營業利益率(%)(營業利益)/(營業收入)",
                "稅前純益率(%)(稅前純益)/(營業收入)",
                "稅後純益率(%)(稅後純益)/(營業收入)"
            ]
            
            if order_by not in valid_fields:
                order_by = "公司代號"  # Default to company code
            
            # Sort data
            def get_sort_key(item):
                value = item.get(order_by, "")
                # Try to convert to float for numeric fields
                if order_by in ["營業收入(百萬元)", "毛利率(%)(營業毛利)/(營業收入)",
                               "營業利益率(%)(營業利益)/(營業收入)", "稅前純益率(%)(稅前純益)/(營業收入)",
                               "稅後純益率(%)(稅後純益)/(營業收入)", "年度", "季別"]:
                    try:
                        return float(value) if value and value != "N/A" else float('-inf')
                    except (ValueError, TypeError):
                        return float('-inf')
                return str(value)
            
            sorted_data = sorted(data, key=get_sort_key, reverse=(order_direction == "desc"))
            
            # Calculate pagination
            total_records = len(sorted_data)
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            total_pages = (total_records + page_size - 1) // page_size
            
            if start_index >= total_records:
                return f"頁碼超出範圍。共有 {total_records} 筆資料，{total_pages} 頁。"
            
            page_data = sorted_data[start_index:end_index]
            
            # Build result
            sort_indicator = "↑" if order_direction == "asc" else "↓"
            result = f"共有 {total_records} 筆營益分析資料 (第 {page_number}/{total_pages} 頁，依 {order_by} {sort_indicator} 排序)：\n\n"
            
            for item in page_data:
                date = item.get("出表日期", "N/A")
                year = item.get("年度", "N/A")
                quarter = item.get("季別", "N/A")
                code = item.get("公司代號", "N/A")
                name = item.get("公司名稱", "N/A")
                revenue = item.get("營業收入(百萬元)", "N/A")
                gross_margin = item.get("毛利率(%)(營業毛利)/(營業收入)", "N/A")
                operating_margin = item.get("營業利益率(%)(營業利益)/(營業收入)", "N/A")
                pretax_margin = item.get("稅前純益率(%)(稅前純益)/(營業收入)", "N/A")
                net_margin = item.get("稅後純益率(%)(稅後純益)/(營業收入)", "N/A")
                
                result += f"- {code} {name} ({year}年Q{quarter}):\n"
                result += f"  營收: {revenue}百萬, 毛利率: {gross_margin}%, 營益率: {operating_margin}%, 稅後淨利率: {net_margin}%\n"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_company_financial_reports_supervisor_acknowledgment(code: str) -> str:
        """Obtain financial report acknowledgment by supervisors for a listed company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap31_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_public_company_balance_sheet(code: str) -> str:
        """Obtain balance sheet for a public company based on its stock code.
        Automatically detects company industry and uses appropriate financial statement format.
        """
        try:
            suffix = _get_industry_api_suffix(code)
            endpoint = f"/opendata/t187ap07_X{suffix}"
            data = TWSEAPIClient.get_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_public_company_income_statement(code: str) -> str:
        """Obtain comprehensive income statement for a public company based on its stock code.
        Automatically detects company industry and uses appropriate financial statement format.
        """
        try:
            suffix = _get_industry_api_suffix(code)
            endpoint = f"/opendata/t187ap06_X{suffix}"
            data = TWSEAPIClient.get_company_data(endpoint, code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_public_company_board_shareholdings(code: str) -> str:
        """Obtain board member shareholding details for a public company based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/opendata/t187ap11_P", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""