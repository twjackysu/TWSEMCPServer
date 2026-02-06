"""Warrants related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records, format_properties_with_values_multiline


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    @mcp.tool
    def get_warrant_basic_info(code: str = "") -> str:
        """
        Get basic information of listed warrants.
        
        Retrieves comprehensive basic data for all listed warrants including warrant codes,
        types, exercise periods, underlying assets, and other key parameters. Can filter
        by specific warrant code if provided.
        
        Args:
            code: Warrant code (optional). If provided, filters results for specific warrant.
                 If empty, returns all warrant basic information.
        
        Returns:
            Formatted string containing warrant basic information including:
            - Report date (出表日期)
            - Warrant code (權證代號)
            - Warrant name (權證簡稱)
            - Warrant type (權證類型)
            - Category (類別)
            - Market maker quoting method (流動量提供者報價方式)
            - Exercise start date (履約開始日)
            - Last trading date (最後交易日)
            - Exercise deadline (履約截止日)
            - Issue size in thousand units (發行單位數量(仟單位))
            - Settlement method (結算方式(詳附註編號說明))
            - Underlying securities/index (標的證券/指數)
            - Latest exercise allocation per thousand units (最新標的履約配發數量(每仟單位權證))
            - Original/latest exercise prices and price limits (原始/最新履約價格及上下限價格)
            - Notes (備註)
        """
        try:
            if code:
                data = TWSEAPIClient.get_company_data("/opendata/t187ap37_L", code)
                return format_properties_with_values_multiline(data) if data else ""
            else:
                data = TWSEAPIClient.get_data("/opendata/t187ap37_L") 
                return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_warrant_daily_trading(code: str = "") -> str:
        """
        Get daily trading data for listed call/put warrants.
        
        Retrieves daily trading volume and value statistics for warrants,
        including transaction amounts and number of contracts traded.
        
        Args:
            code: Warrant code (optional). If provided, filters results for specific warrant.
                 If empty, returns all warrant trading data.
        
        Returns:
            Formatted string containing warrant daily trading data including:
            - Report date (出表日期)
            - Warrant code (權證代號)
            - Warrant name (權證名稱)
            - Trading volume in lots (成交張數)
            - Trading value (成交金額)

        Note:
            This API may return empty data when there are no warrant trades for the day.
            Check warrant basic info to see available warrants before querying trading data.
        """
        try:
            if code:
                data = TWSEAPIClient.get_company_data("/opendata/t187ap42_L", code)
                return format_properties_with_values_multiline(data) if data else ""
            else:
                data = TWSEAPIClient.get_data("/opendata/t187ap42_L")
                return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_warrant_trader_count() -> str:
        """
        Get daily number of warrant traders.
        
        Retrieves statistics on the number of individual traders participating
        in warrant trading on each trading day, providing insights into 
        warrant market participation levels.
        
        Returns:
            Formatted string containing warrant trader count data including:
            - Report date (出表日期)
            - Trading date (日期)
            - Number of traders (人數)
        """
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap43_L")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_warrant_yearly_issuance_statistics() -> str:
        """
        Get yearly issuance statistics for listed call/put warrants.
        
        Retrieves annual issuance statistics and overview for listed call and put warrants,
        as published by Taiwan Stock Exchange (上市認購(售)權證年度發行量概況統計表).
        
        Returns:
            Formatted string containing warrant yearly issuance statistics including:
            - Report date (出表日期)
            - Issuer code (發行人代號)
            - Issuer name (發行人名稱)
            - Warrant code (權證代號)
            - Warrant name (名稱)
            - Underlying asset code (標的代號)
            - Underlying asset name (標的名稱)
            - Application date (申請發行日期)
        """
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap36_L")
            return format_multiple_records(data) if data else ""
        except Exception:
            return ""