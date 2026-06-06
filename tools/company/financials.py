"""Company financial statements tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_properties_with_values_multiline, create_company_tool

# Simple tools: fetch_company_data(endpoint, code) → format as properties.
SIMPLE_FINANCIAL_TOOLS = [
    ("/opendata/t187ap15_L", "get_company_quarterly_earnings_forecast_achievement",
     "根據股票代號查詢上市公司截至各季綜合損益財測達成情形(簡式)。"),
    ("/opendata/t187ap16_L", "get_company_quarterly_audit_variance",
     "根據股票代號查詢上市公司當季綜合損益經會計師查核(核閱)數與當季預測數差異達百分之十以上者(簡式)。"),
    ("/opendata/t187ap17_L", "get_company_profitability_analysis",
     "根據股票代號查詢上市公司營益分析。"),
    ("/opendata/t187ap31_L", "get_company_financial_reports_supervisor_acknowledgment",
     "根據股票代號查詢上市公司財務報告經監察人承認情形。"),
    ("/opendata/t187ap11_P", "get_public_company_board_shareholdings",
     "根據股票代號查詢公發公司董監事持股餘額明細。"),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company financials tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    for endpoint, name, doc in SIMPLE_FINANCIAL_TOOLS:
        create_company_tool(mcp, endpoint, name, doc, client)

    def _get_industry_api_suffix(code: str) -> str:
        """Return API suffix for the company's industry; defaults to '_ci'."""
        try:
            profile_data = _client.fetch_company_data("/opendata/t187ap03_L", code)
            if not profile_data:
                return "_ci"

            industry = profile_data.get("產業別", "")
            industry_mapping = {
                "金融業": "_basi",
                "證券期貨業": "_bd",
                "金控業": "_fh",
                "保險業": "_ins",
                "異業": "_mim",
                "一般業": "_ci",
            }
            for key, suffix in industry_mapping.items():
                if key in industry or industry == key:
                    return suffix
            return "_ci"
        except Exception:
            return "_ci"

    # --- Tools that need industry-specific endpoints ---

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_income_statement(code: str) -> str:
        """根據股票代號查詢上市公司綜合損益表。
        自動偵測公司所屬產業並使用對應的財務報表格式（一般業、金融業、證券期貨業、金控業、保險業、異業）。
        """
        suffix = _get_industry_api_suffix(code)
        data = _client.fetch_company_data(f"/opendata/t187ap06_L{suffix}", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_balance_sheet(code: str) -> str:
        """根據股票代號查詢上市公司資產負債表。
        自動偵測公司所屬產業並使用對應的財務報表格式（一般業、金融業、證券期貨業、金控業、保險業、異業）。
        """
        suffix = _get_industry_api_suffix(code)
        data = _client.fetch_company_data(f"/opendata/t187ap07_L{suffix}", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_public_company_balance_sheet(code: str) -> str:
        """根據股票代號查詢公開發行公司資產負債表。
        自動偵測公司所屬產業並使用對應的財務報表格式。
        """
        suffix = _get_industry_api_suffix(code)
        data = _client.fetch_company_data(f"/opendata/t187ap07_X{suffix}", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_public_company_income_statement(code: str) -> str:
        """根據股票代號查詢公開發行公司綜合損益表。
        自動偵測公司所屬產業並使用對應的財務報表格式。
        """
        suffix = _get_industry_api_suffix(code)
        data = _client.fetch_company_data(f"/opendata/t187ap06_X{suffix}", code)
        return format_properties_with_values_multiline(data) if data else ""

    # --- Tool with custom sorting/pagination ---

    @mcp.tool
    @handle_api_errors()
    def get_company_profitability_analysis_summary(
        page_size: int = 20,
        page_number: int = 1,
        order_by: str = "稅後純益率(%)(稅後純益)/(營業收入)",
        order_direction: str = "desc"
    ) -> str:
        """查詢上市公司營益分析查詢彙總表(全體公司彙總報表)。

        Args:
            page_size: 每頁筆數（預設20，最大100）
            page_number: 頁碼（預設1，從1開始）
            order_by: 排序欄位。可用欄位：公司代號、公司名稱、營業收入(百萬元)、毛利率(%)、營業利益率(%)、稅前純益率(%)、稅後純益率(%)、年度、季別
            order_direction: 排序方向，'asc' 為遞增，'desc' 為遞減（預設 'asc'）
        """
        data = _client.fetch_data("/opendata/t187ap17_L")
        if not data:
            return "目前沒有營益分析查詢彙總表資料。"

        page_size = min(max(1, page_size), 100)
        page_number = max(1, page_number)
        order_direction = order_direction.lower()
        if order_direction not in ["asc", "desc"]:
            order_direction = "asc"

        valid_fields = [
            "公司代號", "公司名稱", "年度", "季別",
            "營業收入(百萬元)",
            "毛利率(%)(營業毛利)/(營業收入)",
            "營業利益率(%)(營業利益)/(營業收入)",
            "稅前純益率(%)(稅前純益)/(營業收入)",
            "稅後純益率(%)(稅後純益)/(營業收入)",
        ]
        if order_by not in valid_fields:
            order_by = "公司代號"

        def get_sort_key(item):
            value = item.get(order_by, "")
            if order_by in ["營業收入(百萬元)", "毛利率(%)(營業毛利)/(營業收入)",
                            "營業利益率(%)(營業利益)/(營業收入)", "稅前純益率(%)(稅前純益)/(營業收入)",
                            "稅後純益率(%)(稅後純益)/(營業收入)", "年度", "季別"]:
                try:
                    return float(value) if value and value != "N/A" else float('-inf')
                except (ValueError, TypeError):
                    return float('-inf')
            return str(value)

        sorted_data = sorted(data, key=get_sort_key, reverse=(order_direction == "desc"))

        total_records = len(sorted_data)
        start_index = (page_number - 1) * page_size
        total_pages = (total_records + page_size - 1) // page_size

        if start_index >= total_records:
            return f"頁碼超出範圍。共有 {total_records} 筆資料，{total_pages} 頁。"

        page_data = sorted_data[start_index:start_index + page_size]
        sort_indicator = "↑" if order_direction == "asc" else "↓"
        result = f"共有 {total_records} 筆營益分析資料 (第 {page_number}/{total_pages} 頁，依 {order_by} {sort_indicator} 排序)：\n\n"

        for item in page_data:
            year = item.get("年度", "N/A")
            quarter = item.get("季別", "N/A")
            code = item.get("公司代號", "N/A")
            name = item.get("公司名稱", "N/A")
            revenue = item.get("營業收入(百萬元)", "N/A")
            gross_margin = item.get("毛利率(%)(營業毛利)/(營業收入)", "N/A")
            operating_margin = item.get("營業利益率(%)(營業利益)/(營業收入)", "N/A")
            net_margin = item.get("稅後純益率(%)(稅後純益)/(營業收入)", "N/A")
            result += f"- {code} {name} ({year}年Q{quarter}):\n"
            result += f"  營收: {revenue}百萬, 毛利率: {gross_margin}%, 營益率: {operating_margin}%, 稅後淨利率: {net_margin}%\n"

        return result
