"""Foreign investment related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    def get_foreign_investment_by_industry() -> str:
        """
        Get foreign and mainland China investment holding ratios by industry category.
        
        Returns comprehensive statistics of foreign investment holdings across different 
        industry sectors in the Taiwan stock market, including the number of companies,
        total issued shares, foreign holdings, and holding percentages by industry.
        
        Returns:
            Formatted string containing foreign investment statistics by industry including:
            - Industry category (產業別)
            - Number of companies (家數) 
            - Total issued shares (總發行股數)
            - Foreign and mainland China total holdings (僑外資及陸資持有總股數)
            - Foreign and mainland China holding percentage (僑外資及陸資持股比率)
        """
        try:
            data = _client.fetch_data("/fund/MI_QFIIS_cat")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool  
    def get_top_foreign_holdings() -> str:
        """
        Get top 20 companies by foreign and mainland China investment holdings.
        
        Returns the ranking of companies with highest foreign investment holdings,
        including detailed information about investment limits, current holdings,
        and available investment capacity for each company.
        
        Returns:
            Formatted string containing top 20 foreign holdings including:
            - Ranking (排行)
            - Stock code (證券代號) 
            - Stock name (證券名稱)
            - Issued shares (發行股數)
            - Available investment shares (外資及陸資尚可投資股數)
            - Current foreign holdings (全體外資及陸資持有股數)
            - Available investment ratio (全體外資及陸資尚可投資比率)
            - Current holding ratio (全體外資及陸資持股比率)
            - Investment upper limit (投資上限)
        """
        try:
            data = _client.fetch_data("/fund/MI_QFIIS_sort_20")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""