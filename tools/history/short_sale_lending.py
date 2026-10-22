"""TWSE short-sale (融券) and securities-lending (借券) balance/trading history.

Complements tools/history/margin_balance.py's MI_MARGN (融資融券餘額), which does not
cover the securities-lending (借券) side of short selling. Balances come from TWT93U through
sources/twse/twt93u.py.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    DEFAULT_DISPLAY_LIMIT,
    SUMMARY_ROW_LABELS,
    Page,
    printed,
)
from toolkit import Limit, Offset, RequiredTradingDate, handle_api_errors
from sources.twse.twt93u import short_sale_lending_balances

TWTASU_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE short-sale/securities-lending history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_short_sale_lending_balance_history(date: RequiredTradingDate, stock_no: str = "", name: str = "",
                                                limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢信用額度總量管制餘額表：融券賣出餘額與借券賣出餘額。
        與 get_margin_balance（融資融券）不同，此工具涵蓋借券賣出（證券出借）的餘額面。

        回傳：每支股票的融券（前日餘額/賣出/買進/現券/今日餘額/次一營業日限額）及
        借券（前日餘額/當日賣出/當日還券/當日調整/當日餘額/次一營業日可限額；2012-03-16 以前證交所公布的是
        前日餘額/賣出/庫存異動/今日餘額/可使用額度）

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        day = short_sale_lending_balances(_client, date)
        if day is None:
            return f"查無 {date} 的信用額度總量管制餘額資料，請確認該日期為交易日（非假日或週末）"

        rows = day.rows  # without the 合計 row
        if not rows:
            return f"查無 {date} 的信用額度總量管制餘額資料"

        if stock_no:
            rows = [r for r in rows if r.code == stock_no]
            if not rows:
                return f"查無股票代號 {stock_no} 在 {date} 的信用額度總量管制餘額資料"
        if name:
            rows = [r for r in rows if name in r.name]
            if not rows:
                return f"查無名稱包含「{name}」的股票在 {date} 的信用額度總量管制餘額資料"

        paged = Page(limit, offset).take(rows)
        if paged.past_end:
            return paged.out_of_range(f"{date} 的信用額度總量管制餘額資料")

        title = day.title or f"{date} 信用額度總量管制餘額表"
        header = f"【{title}】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for r in paged.rows:
            s, b = r.short, r.lending
            if b.old_layout:
                lending = (f"前日{printed(b.previous)} 賣出{printed(b.sold)} 庫存異動{printed(b.inventory_change)} "
                           f"今日{printed(b.today)} 可使用額度{printed(b.available)}")
            else:
                lending = (f"前日{printed(b.previous)} 當日賣出{printed(b.sold)} 當日還券{printed(b.returned)} "
                           f"調整{printed(b.adjusted)} 當日{printed(b.today)} 次日可限額{printed(b.next_day_limit)}")
            lines.append(
                f"{r.code} {r.name}\n"
                f"  融券: 前日{printed(s.previous)} 賣出{printed(s.sold)} 買進{printed(s.bought)} 現券{printed(s.cash_returned)} "
                f"今日{printed(s.today)} 次日限額{printed(s.next_day_limit)}\n"
                f"  借券: {lending}"
            )

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_short_sale_lending_trades_history(date: RequiredTradingDate, stock_no: str = "", name: str = "",
                                               limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢當日融券賣出與借券賣出成交量值。
        與 get_short_sale_lending_balance_history（餘額）互補，此工具是「當日實際成交」的量與金額。

        回傳：每支股票的融券賣出成交數量/金額、借券賣出成交數量/金額

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
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
            # TWTASU 的末列 row[0] 就是「合計」，split 會把它當成股票代號
            if code in SUMMARY_ROW_LABELS:
                continue
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

        paged = Page(limit, offset).take(parsed)
        if paged.past_end:
            return paged.out_of_range(f"{date} 的融券借券賣出成交量值資料")

        title = resp.get("title", f"{date} 當日融券賣出與借券賣出成交量值")
        header = f"【{title}】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for code, sname, row in paged.rows:
            # row: 證券名稱(含代號),融券賣出數量,融券賣出金額,借券賣出數量,借券賣出金額
            ss_vol, ss_val, sl_vol, sl_val = row[1], row[2], row[3], row[4]
            lines.append(
                f"{code} {sname} | 融券賣出: 量{ss_vol} 金額{ss_val} | 借券賣出: 量{sl_vol} 金額{sl_val}"
            )

        if paged.more():
            lines.append("\n" + paged.more())

        return "\n".join(lines)
