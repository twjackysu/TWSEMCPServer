"""OTC trading warning and disposal stocks from TPEx openapi."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

TPEX_WARNING_URL = "https://www.tpex.org.tw/openapi/v1/tpex_trading_warning_information"
TPEX_DISPOSAL_URL = "https://www.tpex.org.tw/openapi/v1/tpex_disposal_information"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC trading warning and disposal tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_warning_stocks(stock_no: str = "") -> str:
        """查詢上櫃注意股票，列出當前被列為交易注意的上櫃股票及其警示原因。
        可指定股票代號查詢特定股票是否在注意名單。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票資料

        Returns:
            注意股票代號、名稱、注意事由、收盤價、本益比
        """
        data = _client.fetch_json(TPEX_WARNING_URL)

        if not isinstance(data, list) or not data:
            return "目前無上櫃注意股票資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"上櫃股票代號 {stock_no} 目前不在注意名單"

        lines = [f"【上櫃注意股票】（共 {len(data)} 筆）\n"]
        for item in data:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            info = item.get("TradingInformation", "-")
            close = item.get("ClosePrice", "-")
            lines.append(f"{code} {name} | 收盤: {close} | 注意事由: {info}")

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_otc_disposal_stocks(stock_no: str = "") -> str:
        """查詢上櫃處置股票，列出當前被列為交易處置的上櫃股票、處置期間及原因。
        可指定股票代號查詢特定股票是否在處置名單。

        Args:
            stock_no: 股票代號（選填），若指定則只回傳該股票資料

        Returns:
            處置股票代號、名稱、處置期間、處置原因、處置條件
        """
        data = _client.fetch_json(TPEX_DISPOSAL_URL)

        if not isinstance(data, list) or not data:
            return "目前無上櫃處置股票資料"

        if stock_no:
            data = [d for d in data if d.get("SecuritiesCompanyCode", "").strip() == stock_no]
            if not data:
                return f"上櫃股票代號 {stock_no} 目前不在處置名單"

        lines = [f"【上櫃處置股票】（共 {len(data)} 筆）\n"]
        for item in data:
            code = item.get("SecuritiesCompanyCode", "?")
            name = item.get("CompanyName", "?")
            period = item.get("DispositionPeriod", "-")
            reasons = item.get("DispositionReasons", "-")
            lines.append(f"{code} {name} | 處置期間: {period} | 原因: {reasons}")

        return "\n".join(lines)
