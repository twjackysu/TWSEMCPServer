"""Real-time stock quote tools using TWSE mis.twse.com.tw API."""

import requests
import logging
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

logger = logging.getLogger(__name__)

REALTIME_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def _fetch_realtime(code: str) -> dict | None:
    """Fetch real-time quote from TWSE matching system."""
    try:
        resp = requests.get(
            REALTIME_URL,
            params={"ex_ch": f"tse_{code}.tw"},
            headers={"User-Agent": "stock-mcp/1.0"},
            verify=False,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        arr = data.get("msgArray", [])
        return arr[0] if arr else None
    except Exception as e:
        logger.error(f"Failed to fetch realtime data for {code}: {e}")
        return None


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register real-time trading tools with the MCP instance."""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_realtime_quote(code: str) -> str:
        """Get real-time intraday quote for a TWSE-listed stock.

        Returns the latest matching-system data including current price, OHLC,
        volume, best 5 bid/ask prices and volumes. Updated every few seconds
        during market hours (09:00-13:30 TST).

        Use this instead of get_stock_daily_trading when you need today's
        intraday data before the market close batch update.

        Returns information including:
        - 股票代號/名稱
        - 即時成交價 (last trade price)
        - 開盤價/最高價/最低價
        - 昨收價 and 漲跌
        - 累積成交量 (shares)
        - 最佳五檔買賣價量
        - 漲停價/跌停價
        - 資料時間
        """
        raw = _fetch_realtime(code)
        if not raw:
            return f"查無即時報價資料（股票代號 {code}），可能非交易時段或代號有誤。"

        name = raw.get("n", "N/A")
        last = raw.get("z", "-")
        open_p = raw.get("o", "-")
        high = raw.get("h", "-")
        low = raw.get("l", "-")
        yesterday = raw.get("y", "-")
        volume = raw.get("v", "-")
        time_ = raw.get("t", "-")
        date_ = raw.get("d", "-")
        upper = raw.get("u", "-")
        lower = raw.get("w", "-")

        # Calculate change
        change_str = ""
        try:
            if last != "-" and yesterday != "-":
                chg = float(last) - float(yesterday)
                pct = (chg / float(yesterday)) * 100
                sign = "+" if chg >= 0 else ""
                change_str = f"{sign}{chg:.2f} ({sign}{pct:.2f}%)"
        except (ValueError, ZeroDivisionError):
            change_str = "N/A"

        # Parse best 5 bid/ask
        asks = raw.get("a", "").rstrip("_").split("_")
        bids = raw.get("b", "").rstrip("_").split("_")
        ask_vols = raw.get("f", "").rstrip("_").split("_")
        bid_vols = raw.get("g", "").rstrip("_").split("_")

        result = f"【{name} ({code})】即時報價\n\n"
        result += f"日期: {date_}\n"
        result += f"時間: {time_}\n"
        result += f"成交價: {last}\n"
        result += f"開盤價: {open_p}\n"
        result += f"最高價: {high}\n"
        result += f"最低價: {low}\n"
        result += f"昨收價: {yesterday}\n"
        result += f"漲跌: {change_str}\n"
        result += f"累積成交量: {volume} 張\n"
        result += f"漲停價: {upper}\n"
        result += f"跌停價: {lower}\n"

        if asks and asks[0]:
            result += "\n賣出五檔:\n"
            for i, (p, v) in enumerate(zip(asks, ask_vols), 1):
                result += f"  賣{i}: {p} ({v} 張)\n"

        if bids and bids[0]:
            result += "\n買入五檔:\n"
            for i, (p, v) in enumerate(zip(bids, bid_vols), 1):
                result += f"  買{i}: {p} ({v} 張)\n"

        return result
