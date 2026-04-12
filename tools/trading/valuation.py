"""Stock valuation tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    format_properties_with_values_multiline,
    MSG_NO_DATA_FOR_CODE,
    handle_api_errors,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register valuation tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_valuation_ratios(code: str) -> str:
        """根據股票代號查詢上市個股日本益比、殖利率及股價淨值比（依代碼查詢）。

        回傳資訊包含日期、代號、名稱、本益比、殖利率(%)、股價淨值比。
        """
        data = _client.fetch_company_data("/exchangeReport/BWIBBU_ALL", code)
        if not data:
            return MSG_NO_DATA_FOR_CODE.format(query_target=f"股票代號 {code}", data_type="本益比等評價指標資料")
        
        result = f"【{data.get('Name', 'N/A')} ({data.get('Code', code)})】評價指標\n\n"
        
        date = data.get("Date", "N/A")
        pe_ratio = data.get("PEratio", "N/A")
        dividend_yield = data.get("DividendYield", "N/A")
        pb_ratio = data.get("PBratio", "N/A")
        
        result += f"日期: {date}\n"
        result += f"本益比 (P/E): {pe_ratio}\n"
        result += f"殖利率 (%): {dividend_yield}\n"
        result += f"股價淨值比 (P/B): {pb_ratio}\n"
        
        return result