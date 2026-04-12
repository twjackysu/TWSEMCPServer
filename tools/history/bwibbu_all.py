"""Market-wide valuation ratios (P/E, dividend yield, P/B) from legacy TWSE endpoint."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

BWIBBU_ALL_URL = "https://www.twse.com.tw/exchangeReport/BWIBBU_ALL"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market valuation tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_market_valuation_by_date(date: str, stock_no: str = "") -> str:
        """查詢全市場上市股票的本益比（P/E）、殖利率、股價淨值比（P/B）。
        適合用於篩選低估值個股或比較產業估值水位。
        可指定特定股票代號只查單一個股。

        Args:
            date: 查詢日期 YYYYMMDD，回傳該日的估值資料
            stock_no: 股票代號（選填），若指定則只回傳該股票的估值資料

        Returns:
            每支股票的代號、名稱、本益比、殖利率(%)、股價淨值比
        """
        resp = _client.fetch_json(
            BWIBBU_ALL_URL,
            params={"response": "json", "date": date},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的估值資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的估值資料"

        # Filter by stock_no if specified
        if stock_no:
            data = [row for row in data if row[0].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的估值資料"

        lines = [f"【全市場估值資料 - {date}】（共 {len(data)} 筆）\n"]

        for row in data:
            # row: [股票代號, 名稱, 本益比, 殖利率(%), 股價淨值比]
            code = row[0].strip()
            name = row[1].strip()
            pe = row[2] if row[2] else "-"
            dy = row[3] if row[3] else "-"
            pb = row[4] if row[4] else "-"
            lines.append(f"{code} {name} | 本益比: {pe} | 殖利率: {dy}% | 股價淨值比: {pb}")

        return "\n".join(lines)
