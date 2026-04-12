"""Market-wide margin trading balance data from legacy TWSE endpoint."""

from datetime import datetime, timedelta
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

MI_MARGN_URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"
MAX_RETRY_DAYS = 7


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register margin balance tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_margin_balance(date: str, stock_no: str = "") -> str:
        """查詢全市場融資融券餘額，用於判斷市場槓桿水位與多空情緒。
        若指定日期非交易日，會自動往前尋找最近的交易日資料。
        可指定特定股票代號只查單一個股。

        Args:
            date: 查詢日期 YYYYMMDD
            stock_no: 股票代號（選填），若指定則只回傳該股票的融資融券資料

        Returns:
            每支股票的融資買進、賣出、餘額、融券賣出、買進、餘額、資券互抵等資料
        """
        current_date = datetime.strptime(date, "%Y%m%d")

        resp = None
        actual_date = date
        for _ in range(MAX_RETRY_DAYS):
            actual_date = current_date.strftime("%Y%m%d")
            resp = _client.fetch_json(
                MI_MARGN_URL,
                params={"response": "json", "date": actual_date, "selectType": "ALL"},
            )
            if resp and resp.get("stat") == "OK":
                break
            current_date -= timedelta(days=1)
        else:
            return f"查無 {date} 前後的融資融券資料"

        # MI_MARGN uses "tables" structure:
        #   tables[0] = summary (融資融券彙總)
        #   tables[1] = per-stock detail (個股明細)
        tables = resp.get("tables", [])
        if len(tables) < 2:
            return f"查無 {actual_date} 的融資融券資料"

        per_stock = tables[1]
        data = per_stock.get("data", [])
        fields = per_stock.get("fields", [])

        if not data:
            return f"查無 {actual_date} 的融資融券資料"

        # Filter by stock_no if specified (first column is stock code)
        if stock_no:
            data = [row for row in data if len(row) > 0 and row[0].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {actual_date} 的融資融券資料"

        date_note = f"（原查詢 {date}，實際資料日 {actual_date}）" if actual_date != date else ""
        lines = [f"【融資融券餘額 - {actual_date}】{date_note}（共 {len(data)} 筆）\n"]

        if fields:
            lines.append("欄位: " + " | ".join(fields) + "\n")

        for row in data:
            lines.append(" | ".join(str(cell) for cell in row))

        return "\n".join(lines)
