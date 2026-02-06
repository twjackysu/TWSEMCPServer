"""Other tools for TWSE data."""

from fastmcp import FastMCP
from typing import Optional
from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    handle_api_errors,
    format_list_response,
    create_simple_list_formatter,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register other tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    @handle_api_errors(data_type="基金基本")
    def get_fund_basic_info() -> str:
        """Get basic information summary for all funds."""
        data = _client.fetch_data("/opendata/t187ap47_L")
        if not data:
            return MSG_NO_DATA.format(data_type="基金基本")
        
        formatter = create_simple_list_formatter("基金名稱", "基金代號", "基金類型")
        return format_list_response(data, "基金基本資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="中央登錄公債補息")
    def get_central_depository_bond_redemption() -> str:
        """Get central depository bond redemption data."""
        data = _client.fetch_data("/exchangeReport/BFI61U")
        if not data:
            return MSG_NO_DATA.format(data_type="中央登錄公債補息")
        
        formatter = create_simple_list_formatter("Name", "Code", "StartingDate")
        return format_list_response(data, "中央登錄公債補息資料", formatter)

    @mcp.tool
    @handle_api_errors(data_type="有價證券集中交易市場開（休）市日期")
    def get_market_holiday_schedule() -> str:
        """Get holiday schedule for securities centralized trading market."""
        data = _client.fetch_data("/holidaySchedule/holidaySchedule")
        if not data:
            return MSG_NO_DATA.format(data_type="有價證券集中交易市場開（休）市日期")
        
        def formatter(item):
            name = item.get("Name", "N/A")
            date = item.get("Date", "N/A")
            weekday = item.get("Weekday", "N/A")
            description = item.get("Description", "N/A")
            return f"- {date} ({weekday}) {name}: {description}\n"
        
        return format_list_response(data, "有價證券集中交易市場開（休）市日期", formatter, limit=50)