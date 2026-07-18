"""TWSE short-sale (融券) and securities-lending (借券) balance/trading history.

Complements tools/history/margin_balance.py's MI_MARGN (融資融券餘額), which does not
cover the securities-lending (借券) side of short selling.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

TWT93U_URL = "https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U"
TWTASU_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE short-sale/securities-lending history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_short_sale_lending_balance_history(date: str, stock_no: str = "", name: str = "",
                                                limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢信用額度總量管制餘額表：融券賣出餘額與借券賣出餘額。
        與 get_margin_balance（融資融券）不同，此工具涵蓋借券賣出（證券出借）的餘額面。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的融券（前日餘額/賣出/買進/現券/今日餘額/次一營業日限額）及
            借券（前日餘額/當日賣出/當日還券/當日調整/當日餘額/次一營業日可限額）
        """
        resp = _client.fetch_json(
            TWT93U_URL,
            params={"response": "json", "date": date, "selectType": "ALL"},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的信用額度總量管制餘額資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的信用額度總量管制餘額資料"

        if stock_no:
            data = [row for row in data if row[0].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的信用額度總量管制餘額資料"
        if name:
            data = [row for row in data if name in row[1]]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {date} 的信用額度總量管制餘額資料"

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        title = resp.get("title", f"{date} 信用額度總量管制餘額表")
        header = f"【{title}】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for row in page_data:
            # row: 代號,名稱,前日餘額,賣出,買進,現券,今日餘額,次一營業日限額,
            #      前日餘額,當日賣出,當日還券,當日調整,當日餘額,次一營業日可限額,備註
            code, sname = row[0], row[1]
            ss_prev, ss_sell, ss_buy, ss_cash, ss_today, ss_limit = row[2:8]
            sl_prev, sl_sell, sl_return, sl_adjust, sl_today, sl_limit = row[8:14]
            lines.append(
                f"{code} {sname}\n"
                f"  融券: 前日{ss_prev} 賣出{ss_sell} 買進{ss_buy} 現券{ss_cash} 今日{ss_today} 次日限額{ss_limit}\n"
                f"  借券: 前日{sl_prev} 當日賣出{sl_sell} 當日還券{sl_return} 調整{sl_adjust} 當日{sl_today} 次日可限額{sl_limit}"
            )

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_short_sale_lending_trades_history(date: str, stock_no: str = "", name: str = "",
                                               limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢當日融券賣出與借券賣出成交量值。
        與 get_short_sale_lending_balance_history（餘額）互補，此工具是「當日實際成交」的量與金額。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的融券賣出成交數量/金額、借券賣出成交數量/金額
        """
        resp = _client.fetch_json(
            TWTASU_URL,
            params={"response": "json", "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的融券借券賣出成交量值資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的融券借券賣出成交量值資料"

        # row[0] combines code and name in one padded string, e.g. "2330   台積電"
        parsed = []
        for row in data:
            code_name = row[0].split(None, 1)
            code = code_name[0] if code_name else ""
            sname = code_name[1].strip() if len(code_name) > 1 else ""
            parsed.append((code, sname, row))

        if stock_no:
            parsed = [p for p in parsed if p[0] == stock_no]
            if not parsed:
                return f"查無股票代號 {stock_no} 在 {date} 的融券借券賣出成交量值資料"
        if name:
            parsed = [p for p in parsed if name in p[1]]
            if not parsed:
                return f"查無名稱包含「{name}」的股票在 {date} 的融券借券賣出成交量值資料"

        total = len(parsed)
        page_data = parsed[offset:offset + limit]
        end = min(offset + limit, total)

        title = resp.get("title", f"{date} 當日融券賣出與借券賣出成交量值")
        header = f"【{title}】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for code, sname, row in page_data:
            # row: 證券名稱(含代號),融券賣出數量,融券賣出金額,借券賣出數量,借券賣出金額
            ss_vol, ss_val, sl_vol, sl_val = row[1], row[2], row[3], row[4]
            lines.append(
                f"{code} {sname} | 融券賣出: 量{ss_vol} 金額{ss_val} | 借券賣出: 量{sl_vol} 金額{sl_val}"
            )

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
