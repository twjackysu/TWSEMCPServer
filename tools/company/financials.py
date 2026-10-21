"""Company financial report tools from the TWSE OpenAPI (forecast achievement, profitability
analysis, etc.). The statements themselves (損益表/資產負債表/現金流量表) live in
tools/mops/financial_statements.py."""

from typing import List, Literal, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, Page
from toolkit import CompanyToolSpec, create_company_tool, handle_api_errors

# One summary row is two lines; more than this per reply is past what a model can use.
MAX_PROFITABILITY_ROWS = 100

# order_by names shown to callers → t187ap17_L column names. The full column names are
# accepted too: the previous default was one, so earlier callers may still send it.
PROFITABILITY_SORT_FIELDS = {
    "公司代號": "公司代號",
    "公司名稱": "公司名稱",
    "年度": "年度",
    "季別": "季別",
    "營業收入(百萬元)": "營業收入(百萬元)",
    "毛利率(%)": "毛利率(%)(營業毛利)/(營業收入)",
    "營業利益率(%)": "營業利益率(%)(營業利益)/(營業收入)",
    "稅前純益率(%)": "稅前純益率(%)(稅前純益)/(營業收入)",
    "稅後純益率(%)": "稅後純益率(%)(稅後純益)/(營業收入)",
}
TEXT_SORT_FIELDS = {"公司代號", "公司名稱"}


def profitability_sort_field(order_by: str) -> str:
    """The t187ap17_L column for ``order_by``; an unknown name is an error, never a silent fallback."""
    order_by = order_by.strip()
    if order_by in PROFITABILITY_SORT_FIELDS:
        return PROFITABILITY_SORT_FIELDS[order_by]
    if order_by in PROFITABILITY_SORT_FIELDS.values():
        return order_by
    raise ToolError(f"order_by 必須是 {'、'.join(PROFITABILITY_SORT_FIELDS)} 其中之一，收到：{order_by}")

# Simple tools: fetch_company_data(endpoint, code) → format as properties.
SIMPLE_FINANCIAL_TOOLS: List[CompanyToolSpec] = [
    CompanyToolSpec("/opendata/t187ap15_L", "get_company_quarterly_earnings_forecast_achievement",
                    "根據股票代號查詢上市公司截至各季綜合損益財測達成情形(簡式)。"),
    CompanyToolSpec("/opendata/t187ap16_L", "get_company_quarterly_audit_variance",
                    "根據股票代號查詢上市公司當季綜合損益經會計師查核(核閱)數與當季預測數差異達百分之十以上者(簡式)。"),
    CompanyToolSpec("/opendata/t187ap17_L", "get_company_profitability_analysis",
                    "根據股票代號查詢上市公司營益分析。"),
    CompanyToolSpec("/opendata/t187ap31_L", "get_company_financial_reports_supervisor_acknowledgment",
                    "根據股票代號查詢上市公司財務報告經監察人承認情形。"),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company financials tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    for spec in SIMPLE_FINANCIAL_TOOLS:
        create_company_tool(mcp, spec, client)

    # --- Tool with custom sorting/pagination ---

    @mcp.tool
    @handle_api_errors()
    def get_company_profitability_analysis_summary(
        order_by: str = "稅後純益率(%)",
        order_direction: Literal["asc", "desc"] = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """查詢上市公司營益分析查詢彙總表(全體公司彙總報表)。

        Args:
            order_by: 排序欄位（預設 稅後純益率(%)）。可用欄位：公司代號、公司名稱、營業收入(百萬元)、毛利率(%)、營業利益率(%)、稅前純益率(%)、稅後純益率(%)、年度、季別
            order_direction: 排序方向，'asc' 為遞增，'desc' 為遞減（預設 'desc'）
            limit: 回傳筆數上限（預設 20，最多 100）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        order_by = profitability_sort_field(order_by)
        page = Page(limit, offset, max_limit=MAX_PROFITABILITY_ROWS)
        data = _client.fetch_data("/opendata/t187ap17_L")
        if not data:
            return "目前沒有營益分析查詢彙總表資料。"

        def get_sort_key(item):
            value = item.get(order_by, "")
            if order_by not in TEXT_SORT_FIELDS:
                try:
                    return float(value) if value and value != "N/A" else float('-inf')
                except (ValueError, TypeError):
                    return float('-inf')
            return str(value)

        paged = page.take(sorted(data, key=get_sort_key, reverse=(order_direction == "desc")))
        if paged.past_end:
            return paged.out_of_range("營益分析資料")

        sort_indicator = "↑" if order_direction == "asc" else "↓"
        span = f"{paged.span()}，" if paged.span() else ""
        result = f"共有 {paged.total} 筆營益分析資料 ({span}依 {order_by} {sort_indicator} 排序)：\n\n"

        for item in paged.rows:
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

        if paged.more():
            result += "\n" + paged.more()
        return result
