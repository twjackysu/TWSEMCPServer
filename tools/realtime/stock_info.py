"""Real-time stock quote tool from mis.twse.com.tw."""

from typing import List, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register real-time quote tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_realtime_quote(stock_nos: List[str]) -> str:
        """查詢台灣股票盤中即時報價，支援同時查詢多支股票。
        上市股與上櫃股皆可查，系統自動判斷前綴。
        盤後回傳最後成交價。

        Args:
            stock_nos: 股票代號列表，例如 ["2330", "0050", "2317"]

        Returns:
            每支股票的即時報價：代號、名稱、成交價、開盤、最高、最低、昨收、成交量、漲跌、漲跌幅、時間
        """
        if not stock_nos:
            return "請提供至少一個股票代號"

        # Build ex_ch parameter: try tse_ first for all stocks
        # Format: tse_2330.tw|tse_0050.tw|otc_6547.tw
        ex_ch_parts = []
        for code in stock_nos:
            code = code.strip()
            # OTC stocks typically have codes starting with certain patterns,
            # but we'll try tse_ first and check results
            ex_ch_parts.append(f"tse_{code}.tw")

        ex_ch = "|".join(ex_ch_parts)
        resp = _client.fetch_json(MIS_URL, params={"ex_ch": ex_ch, "json": 1, "delay": 0})

        msg_array = resp.get("msgArray", [])

        # Check for stocks that returned no data (might be OTC)
        found_codes = {item.get("c") for item in msg_array if item.get("z") != "-" or item.get("y")}
        missing = [code.strip() for code in stock_nos if code.strip() not in found_codes]

        # Retry missing stocks with otc_ prefix
        if missing:
            otc_parts = [f"otc_{code}.tw" for code in missing]
            otc_resp = _client.fetch_json(
                MIS_URL, params={"ex_ch": "|".join(otc_parts), "json": 1, "delay": 0}
            )
            otc_array = otc_resp.get("msgArray", [])
            msg_array.extend(otc_array)

        if not msg_array:
            return f"查無 {', '.join(stock_nos)} 的即時報價資料"

        lines = [f"【即時報價】（共 {len(msg_array)} 支）\n"]

        for item in msg_array:
            code = item.get("c", "?")
            name = item.get("n", "?")
            price = item.get("z", "-")       # 成交價
            open_p = item.get("o", "-")       # 開盤價
            high = item.get("h", "-")         # 最高價
            low = item.get("l", "-")          # 最低價
            prev_close = item.get("y", "-")   # 昨收價
            volume = item.get("v", "-")       # 成交量（張）
            timestamp = item.get("t", "-")    # 最後成交時間
            date_ = item.get("d", "-")        # 日期
            upper = item.get("u", "-")        # 漲停價
            lower = item.get("w", "-")        # 跌停價
            market = "上市" if item.get("ex") == "tse" else "上櫃"

            # Calculate change and change%
            change_str = ""
            if price != "-" and prev_close and prev_close != "-":
                try:
                    p = float(price)
                    y = float(prev_close)
                    change = p - y
                    change_pct = (change / y) * 100 if y != 0 else 0
                    sign = "+" if change >= 0 else ""
                    change_str = f" | 漲跌: {sign}{change:.2f} ({sign}{change_pct:.2f}%)"
                except (ValueError, ZeroDivisionError):
                    pass

            lines.append(
                f"{code} {name} [{market}] | "
                f"成交: {price} | 開: {open_p} | 高: {high} | 低: {low} | "
                f"昨收: {prev_close} | 量: {volume}張{change_str} | "
                f"漲停: {upper} | 跌停: {lower} | {date_} {timestamp}"
            )

            # Best 5 bid/ask prices
            asks = item.get("a", "").rstrip("_").split("_")
            ask_vols = item.get("f", "").rstrip("_").split("_")
            bids = item.get("b", "").rstrip("_").split("_")
            bid_vols = item.get("g", "").rstrip("_").split("_")

            if asks and asks[0]:
                ask_parts = [f"{p}({v}張)" for p, v in zip(asks, ask_vols) if p]
                lines.append(f"  賣五檔: {' / '.join(ask_parts)}")
            if bids and bids[0]:
                bid_parts = [f"{p}({v}張)" for p, v in zip(bids, bid_vols) if p]
                lines.append(f"  買五檔: {' / '.join(bid_parts)}")

        return "\n".join(lines)
