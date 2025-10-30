"""Periodic trading data tools (monthly, yearly)."""

from utils import TWSEAPIClient, format_properties_with_values_multiline

def register_tools(mcp):
    """Register periodic trading tools with the MCP instance."""
    
    @mcp.tool
    def get_stock_monthly_average(code: str) -> str:
        """Obtain daily closing price and monthly average price for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/STOCK_DAY_AVG_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""

    @mcp.tool
    def get_stock_monthly_trading(code: str) -> str:
        """Obtain monthly trading information for a listed company stock based on its stock code.
        
        Returns information including:
        - Month: Trading month (ROC calendar YYMM)
        - Code: Stock code
        - Name: Stock name
        - HighestPrice: Highest price in the month
        - LowestPrice: Lowest price in the month
        - WeightedAvgPriceAB: Weighted average price
        - Transaction: Transaction count
        - TradeValueA: Trade value (in TWD)
        - TradeVolumeB: Trade volume (in shares)
        - TurnoverRatio: Turnover ratio (%)
        """
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/FMSRFK_ALL", code)
            if not data:
                return f"查無股票代號 {code} 的月成交資訊"
            
            result = f"【{data.get('Name', 'N/A')} ({data.get('Code', code)})】月成交資訊\n\n"
            
            month = data.get("Month", "N/A")
            highest = data.get("HighestPrice", "N/A")
            lowest = data.get("LowestPrice", "N/A")
            avg_price = data.get("WeightedAvgPriceAB", "N/A")
            transaction = data.get("Transaction", "N/A")
            trade_value = data.get("TradeValueA", "N/A")
            trade_volume = data.get("TradeVolumeB", "N/A")
            turnover = data.get("TurnoverRatio", "N/A")
            
            result += f"月份: {month}\n"
            result += f"最高價: {highest}\n"
            result += f"最低價: {lowest}\n"
            result += f"加權平均價: {avg_price}\n"
            result += f"成交筆數: {transaction}\n"
            result += f"成交金額: {trade_value}\n"
            result += f"成交股數: {trade_volume}\n"
            result += f"週轉率(%): {turnover}\n"
            
            return result
        except Exception as e:
            return f"查詢股票代號 {code} 的月成交資訊時發生錯誤: {str(e)}"

    @mcp.tool
    def get_stock_yearly_trading(code: str) -> str:
        """Obtain yearly trading information for a listed company stock based on its stock code."""
        try:
            data = TWSEAPIClient.get_company_data("/exchangeReport/FMNPTK_ALL", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception:
            return ""