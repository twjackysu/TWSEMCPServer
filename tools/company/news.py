"""News and major announcements related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_multiple_records, format_properties_with_values_multiline, MSG_QUERY_FAILED


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    def get_company_major_news(code: str = "") -> str:
        """查詢上市公司每日重大訊息。

        Args:
            code: 股票代號（選填）。若指定則只回傳該公司的重大訊息。
        """
        try:
            if code:
                data = _client.fetch_company_data("/opendata/t187ap04_L", code)
                return format_properties_with_values_multiline(data) if data else ""
            else:
                data = _client.fetch_data("/opendata/t187ap04_L")
                return format_multiple_records(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_twse_news(start_date: str = "", end_date: str = "") -> str:
        """查詢證交所新聞。

        Args:
            start_date: 起始日期（格式 YYYYMMDD），預設為當月第一天
            end_date: 結束日期（格式 YYYYMMDD），預設為當月最後一天
        """
        try:
            from datetime import datetime, date
            import calendar
            
            # If no dates provided, use current month
            if not start_date and not end_date:
                now = datetime.now()
                # Convert to 民國年 format (subtract 1911 years)
                roc_year = now.year - 1911
                start_date = f"{roc_year:03d}{now.month:02d}01"
                
                # Get last day of current month
                last_day = calendar.monthrange(now.year, now.month)[1]
                end_date = f"{roc_year:03d}{now.month:02d}{last_day:02d}"
            elif start_date and not end_date:
                # If only start_date provided, convert to 民國年 and use same month
                if len(start_date) == 8:  # YYYYMMDD format
                    year = int(start_date[:4]) - 1911
                    month = start_date[4:6]
                    day = start_date[6:8]
                    start_date = f"{year:03d}{month}{day}"
                    
                    # Set end_date to last day of that month
                    orig_year = int(start_date[:4]) + 1911 if len(start_date) == 7 else int(start_date[:3]) + 1911
                    orig_month = int(start_date[3:5]) if len(start_date) == 7 else int(start_date[3:5])
                    last_day = calendar.monthrange(orig_year, orig_month)[1]
                    end_date = f"{year:03d}{month}{last_day:02d}"
            elif not start_date and end_date:
                # If only end_date provided, convert to 民國年 and use same month start
                if len(end_date) == 8:  # YYYYMMDD format
                    year = int(end_date[:4]) - 1911
                    month = end_date[4:6]
                    day = end_date[6:8]
                    end_date = f"{year:03d}{month}{day}"
                    start_date = f"{year:03d}{month}01"
            else:
                # Both dates provided, convert both to 民國年 format
                if len(start_date) == 8:  # YYYYMMDD format
                    year = int(start_date[:4]) - 1911
                    start_date = f"{year:03d}{start_date[4:]}"
                if len(end_date) == 8:  # YYYYMMDD format
                    year = int(end_date[:4]) - 1911
                    end_date = f"{year:03d}{end_date[4:]}"
            
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
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_twse_events(top: int = 10) -> str:
        """查詢證交所活動訊息。

        Args:
            top: 回傳筆數上限（預設10），填0則回傳全部。
        """
        try:
            data = _client.fetch_data("/news/eventList")
            if data and top > 0:
                data = data[:top]
            return format_multiple_records(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))