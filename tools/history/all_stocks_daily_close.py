"""TWSE all-listed-stocks daily closing quotes (whole-market snapshot, any past date)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

MI_INDEX_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"

# The table with per-stock quotes ("每日收盤行情") is a specific entry within the
# `tables` array MI_INDEX returns (the rest are index-level summary tables). Its
# position has been stable across dates tested; located by title prefix as a
# safety net in case TWSE reorders the tables.
STOCK_TABLE_TITLE_PREFIX = "每日收盤行情"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE all-stocks daily close tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_all_stocks_daily_close(date: str, stock_no: str = "", name: str = "",
                                    limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢指定日期全部上市股票的每日收盤行情（開高低收、成交量、本益比）。
        與 get_stock_history（單一股票查一整月）互補：此工具是「單一日期查全市場」，
        適合抓某天的市場快照或篩選特定條件的股票。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的代號、名稱、成交股數、成交金額、開高低收、漲跌、本益比
        """
        resp = _client.fetch_json(
            MI_INDEX_URL,
            params={"response": "json", "date": date, "type": "ALLBUT0999"},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的收盤行情資料，請確認該日期為交易日（非假日或週末）"

        tables = resp.get("tables", [])
        stock_table = next(
            (t for t in tables if (t.get("title") or "").find(STOCK_TABLE_TITLE_PREFIX) != -1),
            None,
        )
        if not stock_table or not stock_table.get("data"):
            return f"查無 {date} 的個股收盤行情資料"

        data = stock_table["data"]
        if stock_no:
            data = [row for row in data if row[0].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的收盤行情"
        if name:
            data = [row for row in data if name in row[1]]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {date} 的收盤行情"

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        header = f"【{date} 全市場每日收盤行情】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for row in page_data:
            # row: 證券代號,證券名稱,成交股數,成交筆數,成交金額,開盤價,最高價,最低價,收盤價,漲跌(+/-),漲跌價差,最後揭示買價,最後揭示買量,最後揭示賣價,最後揭示賣量,本益比
            code, sname, volume, _tx, value, o, h, l, c, _dir, change, _bp, _bv, _ap, _av, pe = row
            lines.append(
                f"{code} {sname} | 開:{o} 高:{h} 低:{l} 收:{c} 漲跌:{change} | "
                f"量:{volume} 金額:{value} | 本益比:{pe}"
            )

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
