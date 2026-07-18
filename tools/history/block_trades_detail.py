"""TWSE block trade (鉅額交易) daily detail, per-transaction."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

BFIAUU_URL = "https://www.twse.com.tw/rwd/zh/block/BFIAUU"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE block trade detail tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_block_trades_detail(date: str, stock_no: str = "", name: str = "",
                                 limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢集中市場鉅額交易逐筆明細（含配對交易、盤後鉅額等交易別）。
        與 get_block_trades_daily（openapi 版，僅有量值統計總數）不同，此工具回傳每一筆
        鉅額交易的個股代號、交易別、成交價與成交量金額。
        注意：來源端點不支援伺服器端股票代號篩選，stock_no/name 為本地端過濾。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票的鉅額交易
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每筆鉅額交易的股票代號、名稱、交易別、成交價、成交股數、成交金額
        """
        resp = _client.fetch_json(
            BFIAUU_URL,
            params={"response": "json", "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的鉅額交易資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的鉅額交易資料"

        if stock_no:
            data = [row for row in data if row[0].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的鉅額交易資料"
        if name:
            data = [row for row in data if name in row[1]]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {date} 的鉅額交易資料"

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        title = resp.get("title", f"{date} 鉅額交易日成交資訊")
        header = f"【{title}】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for row in page_data:
            # row: 證券代號,證券名稱,交易別,成交價,成交股數,成交金額
            code, sname, kind, price, volume, value = row
            lines.append(f"{code} {sname} | {kind} | 價:{price} 量:{volume} 金額:{value}")

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
