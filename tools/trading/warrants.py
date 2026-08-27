"""Warrants related tools for Taiwan Stock Exchange MCP server."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    handle_api_errors,
    format_list_response,
    format_multiple_records,
    format_properties_with_values_multiline,
    DEFAULT_DISPLAY_LIMIT,
)


def _format_warrant_summary(item) -> str:
    """One-line summary of a warrant, omitting the verbose 備註 changelog."""
    return (
        f"- {item.get('權證代號', 'N/A')} {item.get('權證簡稱', 'N/A')}"
        f" | {item.get('權證類型', 'N/A')}/{item.get('類別', 'N/A')}"
        f" | 標的: {item.get('標的證券/指數', 'N/A')}"
        f" | 最新履約價: {item.get('最新履約價格(元)/履約指數', 'N/A')}"
        f" | 最後交易日: {item.get('最後交易日', 'N/A')}\n"
    )


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_warrant_basic_info(code: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市權證基本資料彙總表。

        Args:
            code: 權證代號（選填）。若指定則只回傳該權證資料。
            limit: 未指定 code 時的回傳筆數上限（預設 50）
            offset: 未指定 code 時跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        if code:
            data = _client.fetch_company_data("/opendata/t187ap37_L", code)
            return format_properties_with_values_multiline(data) if data else ""

        # 近 4 萬檔權證，全數展開約 40 MB，必須分頁。清單模式另外省略「備註」——
        # 該欄位是逐筆的增額/註銷流水帳，單筆可逾千字，佔了輸出的絕大部分。
        # 指定 code 時仍回傳完整欄位。
        data = _client.fetch_data("/opendata/t187ap37_L")
        return format_list_response(
            data, "上市權證基本資料", formatter=_format_warrant_summary, limit=limit, offset=offset
        )

    @mcp.tool
    @handle_api_errors()
    def get_warrant_daily_trading(code: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市認購(售)權證每日成交資料檔。

        Args:
            code: 權證代號（選填）。若指定則只回傳該權證成交資料。
            limit: 未指定 code 時的回傳筆數上限（預設 50）
            offset: 未指定 code 時跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        if code:
            data = _client.fetch_company_data("/opendata/t187ap42_L", code)
            return format_properties_with_values_multiline(data) if data else ""

        data = _client.fetch_data("/opendata/t187ap42_L")
        return format_list_response(data, "上市權證每日成交資料", limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_warrant_trader_count() -> str:
        """查詢上市認購(售)權證交易人數檔。"""
        data = _client.fetch_data("/opendata/t187ap43_L")
        return format_multiple_records(data) if data else ""

    @mcp.tool
    @handle_api_errors()
    def get_warrant_yearly_issuance_statistics(limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市認購(售)權證年度發行量概況統計表。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap36_L")
        return format_list_response(data, "上市權證年度發行量統計", limit=limit, offset=offset)
