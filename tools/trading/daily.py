"""Daily trading data tools."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register daily trading tools with the MCP instance."""
    
    @mcp.tool
    def get_stock_daily_trading(code: str) -> str:
        """Obtain daily trading information for a listed company stock based on its stock code.
        
        Returns information including:
        - Date: Trading date (ROC calendar YYYMMDD)
        - Code: Stock code
        - Name: Stock name
        - TradeVolume: Trade volume (in shares)
        - TradeValue: Trade value (in TWD)
        - OpeningPrice: Opening price
        - HighestPrice: Highest price
        - LowestPrice: Lowest price
        - ClosingPrice: Closing price
        - Change: Price change
        - Transaction: Transaction count
        """
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/STOCK_DAY_ALL", code)
            if not data:
                return f"查無股票代號 {code} 的日成交資訊"
            
            result = f"【{data.get('Name', 'N/A')} ({data.get('Code', code)})】日成交資訊\n\n"
            
            date = data.get("Date", "N/A")
            trade_volume = data.get("TradeVolume", "N/A")
            trade_value = data.get("TradeValue", "N/A")
            opening = data.get("OpeningPrice", "N/A")
            highest = data.get("HighestPrice", "N/A")
            lowest = data.get("LowestPrice", "N/A")
            closing = data.get("ClosingPrice", "N/A")
            change = data.get("Change", "N/A")
            transaction = data.get("Transaction", "N/A")
            
            result += f"日期: {date}\n"
            result += f"開盤價: {opening}\n"
            result += f"最高價: {highest}\n"
            result += f"最低價: {lowest}\n"
            result += f"收盤價: {closing}\n"
            result += f"漲跌: {change}\n"
            result += f"成交股數: {trade_volume}\n"
            result += f"成交金額: {trade_value}\n"
            result += f"成交筆數: {transaction}\n"
            
            return result
        except Exception as e:
            return f"查詢股票代號 {code} 的日成交資訊時發生錯誤: {str(e)}"