"""TAIFEX margin requirements for index futures/options and stock futures."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

_INDEX_MARGIN_URL = "https://openapi.taifex.com.tw/v1/IndexFuturesAndOptionsMargining"
_STOCK_MARGIN_URL = "https://openapi.taifex.com.tw/v1/SingleStockFuturesMargining"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_index_futures_margin(contract: str = "") -> str:
        """查詢股價指數類期貨與選擇權保證金一覽表，包含結算保證金、維持保證金、原始保證金。
        留空 contract 則顯示全部商品。

        Args:
            contract: 商品名稱（中文），例如「臺股期貨」。留空則顯示全部。

        Returns:
            各指數期貨／選擇權商品的結算、維持、原始保證金金額（元）
        """
        data = _client.fetch_json(_INDEX_MARGIN_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無股價指數類保證金資料"

        date = data[0].get("Date", "?")

        if contract:
            filtered = [x for x in data if contract in x.get("Contract", "")]
            if not filtered:
                names = sorted(x.get("Contract", "") for x in data)
                return f"查無「{contract}」。可用商品：\n" + "\n".join(names)
            data = filtered

        lines = [f"【股價指數類保證金一覽】{date}\n"]
        for item in data:
            name = item.get("Contract", "?")
            clearing = item.get("ClearingMargin", "-")
            maintenance = item.get("MaintenanceMargin", "-")
            initial = item.get("InitialMargin", "-")
            lines.append(
                f"▶ {name}\n"
                f"  結算保證金: {clearing} 元\n"
                f"  維持保證金: {maintenance} 元\n"
                f"  原始保證金: {initial} 元"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_stock_futures_margin(stock_code: str = "") -> str:
        """查詢股票期貨保證金一覽表，顯示各股票期貨的保證金率及分組級距。
        留空 stock_code 則顯示全部；可輸入股票代號（如 2330）或期貨契約代碼（如 TXF）。

        Args:
            stock_code: 股票代號（如 2330）或期貨契約代碼（如 CAF）。留空則顯示全部。

        Returns:
            各股票期貨的級距分組、結算、維持、原始保證金率
        """
        data = _client.fetch_json(_STOCK_MARGIN_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無股票期貨保證金資料"

        date = data[0].get("Date", "?")

        if stock_code:
            filtered = [
                x for x in data
                if stock_code == x.get("UnderlyingSecurityCode", "")
                or stock_code.upper() == x.get("Contract", "").upper()
            ]
            if not filtered:
                return f"查無股票代號或契約代碼「{stock_code}」的股票期貨保證金資料"
            data = filtered

        lines = [f"【股票期貨保證金一覽】{date}（共 {len(data)} 筆）\n"]
        for item in data:
            contract = item.get("Contract", "?")
            sec_code = item.get("UnderlyingSecurityCode", "?")
            name = item.get("ContractName", "?")
            group = item.get("GroupLevel", "?")
            clearing = item.get("ClearingMarginRate", "-")
            maintenance = item.get("MaintenanceMarginRate", "-")
            initial = item.get("InitialMarginRate", "-")
            lines.append(
                f"▶ {contract}（{sec_code} {name}）{group}\n"
                f"  結算保證金率: {clearing}  維持: {maintenance}  原始: {initial}"
            )
        return "\n".join(lines)
