"""中央銀行 daily inter-bank exchange rates (我國與主要貿易對手通貨對美元之匯率).

The whole BP01D01 file (1993 to date) is read through ``sources.cbc.exchange_rates``; this
module picks the currencies and the days. CBC refreshes the file about monthly, so the latest
weeks may be missing.
"""

from typing import Optional
from fastmcp import FastMCP
from sources.cbc.exchange_rates import exchange_rates
from utils import TWSEAPIClient, plain
from toolkit import TradingDate, handle_api_errors

DEFAULT_DAYS = 10
MAX_DAYS = 120


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register CBC exchange-rate tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_exchange_rates(start_date: TradingDate = "", end_date: TradingDate = "", currency: str = "") -> str:
        """查詢中央銀行公布的每日匯率：新台幣及主要貿易對手通貨對美元匯率（1993 年起）。
        為當日 16:00 銀行間即期交易匯率，適合觀察新台幣升貶與外資動向。
        央行約每月更新一次檔案，最近幾週的資料可能尚未納入。

        回傳：每日各幣別匯率（標示方向，例如 NTD/USD＝1 美元兌多少新台幣、USD/EUR＝1 歐元兌多少美元）

        Args:
            start_date: 起始日期 西元 YYYYMMDD（選填）。未指定時回傳資料中最近 10 個交易日
            end_date: 結束日期 西元 YYYYMMDD（選填，預設到最新）。區間最多回傳 120 個交易日
            currency: 幣別關鍵字（選填），例如 "新台幣"、"NTD"、"JPY"、"人民幣"；可用逗號分隔多個
        """
        table = exchange_rates(_client)
        if table is None:
            return "目前沒有央行匯率資料。"

        keys = [k.strip().upper() for k in currency.split(",") if k.strip()]
        picked = [i for i, c in enumerate(table.currencies) if not keys or any(k in c.upper() for k in keys)]
        if not picked:
            return f"查無幣別「{currency}」，可用幣別: {', '.join(table.currencies)}"

        days = table.days
        if start_date:
            days = [d for d in days if start_date <= f"{d.date:%Y%m%d}" <= (end_date or "99999999")]
        elif end_date:
            days = [d for d in days if f"{d.date:%Y%m%d}" <= end_date][-DEFAULT_DAYS:]
        else:
            days = days[-DEFAULT_DAYS:]
        if not days:
            return f"查無 {start_date}～{end_date or '最新'} 的匯率資料（資料最新至 {table.days[-1].date:%Y%m%d}）"
        note = ""
        if len(days) > MAX_DAYS:
            days = days[-MAX_DAYS:]
            note = f"，僅顯示最後 {MAX_DAYS} 個交易日"

        lines = [f"【中央銀行 主要貿易對手通貨對美元匯率】（資料更新至 {table.last_updated}{note}）"]
        for d in days:
            cells = [f"{table.currencies[i]}:{plain(d.rates[i])}" for i in picked if d.rates[i] is not None]
            lines.append(f"{d.date.isoformat()} | " + " | ".join(cells))
        return "\n".join(lines)
