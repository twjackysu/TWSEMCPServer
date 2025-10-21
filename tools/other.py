"""Other tools for TWSE data."""

from utils import TWSEAPIClient

def register_tools(mcp):
    """Register other tools with the MCP instance."""
    
    @mcp.tool
    def get_fund_basic_info() -> str:
        """Get basic information summary for all funds."""
        try:
            data = TWSEAPIClient.get_data("/opendata/t187ap47_L")
            if not data:
                return "目前沒有基金基本資料。"
            
            result = f"共有 {len(data)} 筆基金基本資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                fund_code = item.get("基金代號", "N/A")
                fund_name = item.get("基金名稱", "N/A")
                fund_type = item.get("基金種類", "N/A")
                result += f"- {fund_name} ({fund_code}): {fund_type}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_central_depository_bond_redemption() -> str:
        """Get central depository bond redemption data."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/BFI61U")
            if not data:
                return "目前沒有中央登錄公債補息資料。"
            
            result = f"共有 {len(data)} 筆中央登錄公債補息資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                bond_code = item.get("債券代號", "N/A")
                bond_name = item.get("債券名稱", "N/A")
                redemption_date = item.get("補息日期", "N/A")
                result += f"- {bond_name} ({bond_code}): {redemption_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_market_holiday_schedule() -> str:
        """Get holiday schedule for securities centralized trading market."""
        try:
            data = TWSEAPIClient.get_data("/holidaySchedule/holidaySchedule")
            if not data:
                return "目前沒有有價證券集中交易市場開（休）市日期資料。"
            
            result = "有價證券集中交易市場開（休）市日期：\n\n"
            for item in data[:50]:  # Show more for holiday schedule
                date = item.get("日期", "N/A")
                is_holiday = item.get("是否為假期", "N/A")
                description = item.get("說明", "N/A")
                result += f"- {date}: {is_holiday} - {description}\n"
            
            if len(data) > 50:
                result += f"\n... 還有 {len(data) - 50} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"