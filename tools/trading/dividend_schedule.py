"""Dividend and rights schedule related tools for Taiwan Stock Exchange MCP server."""

from utils import TWSEAPIClient, format_multiple_records, format_properties_with_values_multiline


def register_tools(mcp):
    @mcp.tool
    def get_dividend_rights_schedule(code: str = "") -> str:
        """
        Get ex-dividend and ex-rights schedule for listed stocks.
        
        Retrieves upcoming and historical ex-dividend/ex-rights dates along with
        detailed information about stock dividends, cash dividends, rights offerings,
        and other corporate actions. Essential for dividend investment strategies.
        
        Args:
            code: Stock code (optional). If provided, filters results for specific company.
                 If empty, returns all upcoming dividend/rights schedules.
        
        Returns:
            Formatted string containing dividend/rights schedule including:
            - Ex-dividend/rights date (除權息日期)
            - Stock code (股票代號)
            - Company name (名稱)
            - Ex-dividend/rights type (除權息)
            - Stock dividend ratio (無償配股率)
            - Rights offering ratio (現金增資配股率)
            - Rights offering price per share (現金增資認購價)
            - Cash dividend (現金股利)
            - Number of shares offered (配股張數)
            - And other corporate action details
        """
        try:
            if code:
                data = TWSEAPIClient.get_company_data("/exchangeReport/TWT48U_ALL", code)
                return format_properties_with_values_multiline(data) if data else ""
            else:
                data = TWSEAPIClient.get_data("/exchangeReport/TWT48U_ALL")
                return format_multiple_records(data) if data else ""
        except Exception:
            return ""