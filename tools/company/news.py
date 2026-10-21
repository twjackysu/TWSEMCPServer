"""News and major announcements related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records
from toolkit import TradingDate, handle_api_errors
from utils.date_helper import roc_date


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_twse_news(start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢證交所新聞。

        Args:
            start_date: 起始日期（格式 西元 YYYYMMDD），預設為當月第一天
            end_date: 結束日期（格式 西元 YYYYMMDD），預設為當月最後一天
        """
        from datetime import datetime
        import calendar
        
        # The news list dates items in ROC 1150930; the inputs are Gregorian 20260930. A missing end
        # defaults to the month of the other end (the current month when both are missing). The
        # month's last day comes from the Gregorian year, which decides leap years (2024-02-29).
        if not start_date and not end_date:
            now = datetime.now()
            start_date = f"{now:%Y%m}01"
            end_date = f"{now:%Y%m}{calendar.monthrange(now.year, now.month)[1]:02d}"
        elif start_date and not end_date:
            end_date = f"{start_date[:6]}{calendar.monthrange(int(start_date[:4]), int(start_date[4:6]))[1]:02d}"
        elif not start_date and end_date:
            start_date = f"{end_date[:6]}01"
        start_date, end_date = roc_date(start_date, sep=""), roc_date(end_date, sep="")
        
        # Get all news data
        data = _client.fetch_data("/news/newsList")
        
        # Filter by date range if dates are provided
        if data and (start_date or end_date):
            filtered_data = []
            for item in data:
                if isinstance(item, dict) and 'Date' in item:
                    item_date = str(item['Date'])
                    if start_date and end_date:
                        if start_date <= item_date <= end_date:
                            filtered_data.append(item)
                    elif start_date:
                        if item_date >= start_date:
                            filtered_data.append(item)
                    elif end_date:
                        if item_date <= end_date:
                            filtered_data.append(item)
            data = filtered_data
        
        return format_multiple_records(data) if data else ""

    @mcp.tool
    @handle_api_errors()
    def get_twse_events(top: int = 10) -> str:
        """查詢證交所活動訊息。

        Args:
            top: 回傳筆數上限（預設10），填0則回傳全部。
        """
        data = _client.fetch_data("/news/eventList")
        if data and top > 0:
            data = data[:top]
        return format_multiple_records(data) if data else ""
