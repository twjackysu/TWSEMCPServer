"""ETF related tools for Taiwan Stock Exchange MCP server."""

from utils import TWSEAPIClient, format_multiple_records


def register_tools(mcp):
    @mcp.tool
    def get_etf_regular_investment_ranking() -> str:
        """
        Get top 10 securities by number of regular investment accounts (定期定額).
        
        Retrieves ranking statistics for both individual stocks and ETFs based on 
        the number of trading accounts using regular investment plans. This data
        helps identify the most popular securities for systematic investment strategies.
        
        Returns:
            Formatted string containing top 10 regular investment rankings including:
            - Ranking number (排序)
            - Stock code (股票代號)
            - Stock name (股票名稱) 
            - Number of stock trading accounts (股票交易戶數)
            - ETF code (ETF代號)
            - ETF name (ETF名稱)
            - Number of ETF trading accounts (ETF交易戶數)
        """
        try:
            data = TWSEAPIClient.get_data("/ETFReport/ETFRank")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""