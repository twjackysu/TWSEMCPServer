"""Stock valuation tools."""

from utils import (
    TWSEAPIClient,
    format_properties_with_values_multiline,
    MSG_NO_DATA_FOR_CODE,
    MSG_QUERY_FAILED_WITH_CODE,
    handle_api_errors,
)

def register_tools(mcp):
    """Register valuation tools with the MCP instance."""
    
    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_valuation_ratios(code: str) -> str:
        """Obtain P/E ratio, dividend yield, and P/B ratio for a listed company stock based on its stock code.
        
        Returns information including:
        - Date: Data date (ROC calendar YYYMMDD)
        - Code: Stock code
        - Name: Stock name
        - PEratio: Price-to-Earnings ratio
        - DividendYield: Dividend yield (%)
        - PBratio: Price-to-Book ratio
        """
        data = TWSEAPIClient.get_company_data("/exchangeReport/BWIBBU_ALL", code)
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
        result += f"股價淊值比 (P/B): {pb_ratio}\n"
        
        return result