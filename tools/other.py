"""Other tools for TWSE data."""

from utils import (
    TWSEAPIClient,
    DEFAULT_DISPLAY_LIMIT,
    MSG_NO_DATA,
    MSG_QUERY_FAILED,
    MSG_TOTAL_RECORDS,
    MSG_MORE_RECORDS,
    handle_api_errors,
)

def register_tools(mcp):
    """Register other tools with the MCP instance."""
    
    @mcp.tool
    @handle_api_errors(data_type="基金基本")
    def get_fund_basic_info() -> str:
        """Get basic information summary for all funds."""
        data = TWSEAPIClient.get_data("/opendata/t187ap47_L")
        if not data:
            return MSG_NO_DATA.format(data_type="基金基本")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="基金基本資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            fund_code = item.get("基金代號", "N/A")
            fund_name = item.get("基金名稱", "N/A")
            fund_type = item.get("基金種類", "N/A")
            result += f"- {fund_name} ({fund_code}): {fund_type}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="中央登錄公債補息")
    def get_central_depository_bond_redemption() -> str:
        """Get central depository bond redemption data."""
        data = TWSEAPIClient.get_data("/exchangeReport/BFI61U")
        if not data:
            return MSG_NO_DATA.format(data_type="中央登錄公債補息")
        
        result = MSG_TOTAL_RECORDS.format(count=len(data), data_type="中央登錄公債補息資料") + "\n\n"
        for item in data[:DEFAULT_DISPLAY_LIMIT]:
            bond_code = item.get("債券代號", "N/A")
            bond_name = item.get("債券名稱", "N/A")
            redemption_date = item.get("補息日期", "N/A")
            result += f"- {bond_name} ({bond_code}): {redemption_date}\n"
        
        if len(data) > DEFAULT_DISPLAY_LIMIT:
            result += MSG_MORE_RECORDS.format(count=len(data) - DEFAULT_DISPLAY_LIMIT)
        
        return result

    @mcp.tool
    @handle_api_errors(data_type="有價證券集中交易市場開（休）市日期")
    def get_market_holiday_schedule() -> str:
        """Get holiday schedule for securities centralized trading market."""
        data = TWSEAPIClient.get_data("/holidaySchedule/holidaySchedule")
        if not data:
            return MSG_NO_DATA.format(data_type="有價證券集中交易市場開（休）市日期")
        
        result = "有價證券集中交易市場開（休）市日期：\n\n"
        holiday_display_limit = 50
        for item in data[:holiday_display_limit]:
            date = item.get("日期", "N/A")
            is_holiday = item.get("是否為假期", "N/A")
            description = item.get("說明", "N/A")
            result += f"- {date}: {is_holiday} - {description}\n"
        
        if len(data) > holiday_display_limit:
            result += MSG_MORE_RECORDS.format(count=len(data) - holiday_display_limit)
        
        return result