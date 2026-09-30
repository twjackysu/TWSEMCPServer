"""Margin trading (融資融券) balances of listed stocks, latest or any past date.

Replaces the OpenAPI /exchangeReport/MI_MARGN tool (get_margin_trading_info): it only
served the latest day and on 2026-09-29 carried the same stocks and values as this
endpoint's per-stock table, without the market-wide 信用交易統計 table.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT, MSG_OFFSET_OUT_OF_RANGE

MI_MARGN_URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"
MAX_RETRY_DAYS = 7


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register margin balance tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_margin_balance(date: str = "", stock_no: str = "", name: str = "",
                           limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市股票融資融券餘額：預設最新交易日，也可指定過去日期，用於判斷槓桿水位與多空情緒。
        若指定日期非交易日，會自動往前尋找最近的交易日資料。
        未指定個股時附上全市場信用交易統計（融資、融券、融資金額）。上櫃股票請用 get_otc_margin_balance。

        Args:
            date: 查詢日期 YYYYMMDD（選填，留空＝最新交易日）
            stock_no: 股票代號（選填），若指定則只回傳該股票的融資融券資料
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）。全市場約 1300 檔，未分頁的完整輸出逾 100KB
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的融資買進、賣出、餘額、融券賣出、買進、餘額、資券互抵等資料
        """
        if not date:
            # 不帶 date 時上游直接回最新交易日
            resp = _client.fetch_json(MI_MARGN_URL, params={"response": "json", "selectType": "ALL"})
            if not resp or resp.get("stat") != "OK":
                return "查無最新交易日的融資融券資料"
            actual_date = resp.get("date") or "最新交易日"
        else:
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
        #   tables[0] = market-wide 信用交易統計 (融資(交易單位), 融券(交易單位), 融資金額(仟元))
        #   tables[1] = per-stock detail (個股明細)
        tables = resp.get("tables", [])
        if len(tables) < 2:
            return f"查無 {actual_date} 的融資融券資料"

        per_stock = tables[1]
        data = per_stock.get("data", [])
        fields = per_stock.get("fields", [])

        if not data:
            return f"查無 {actual_date} 的融資融券資料"

        # Filter by stock_no / name if specified (columns 0 and 1 are code and name)
        if stock_no:
            data = [row for row in data if len(row) > 0 and row[0].strip() == stock_no.strip()]
            if not data:
                return f"查無股票代號 {stock_no} 在 {actual_date} 的融資融券資料"
        if name:
            data = [row for row in data if len(row) > 1 and name in row[1]]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {actual_date} 的融資融券資料"

        total = len(data)
        page = data[offset:offset + limit]
        if not page:
            return MSG_OFFSET_OUT_OF_RANGE.format(
                offset=offset, data_type=f"{actual_date} 的融資融券資料", count=total
            )

        date_note = f"（原查詢 {date}，實際資料日 {actual_date}）" if date and actual_date != date else ""
        page_note = f"，顯示第 {offset + 1}–{offset + len(page)} 筆" if total > len(page) else ""
        lines = [f"【融資融券餘額 - {actual_date}】{date_note}（共 {total} 筆{page_note}）\n"]

        summary_rows = tables[0].get("data") or []
        if summary_rows and not stock_no and not name:
            # row: 項目,買進,賣出,現金(券)償還,前日餘額,今日餘額
            lines.append("全市場信用交易統計（買進/賣出/償還/前日餘額/今日餘額）:")
            for row in summary_rows:
                lines.append("  " + " | ".join(str(cell) for cell in row))
            lines.append("")

        if fields:
            lines.append("欄位: " + " | ".join(fields) + "\n")

        for row in page:
            lines.append(" | ".join(str(cell) for cell in row))

        remaining = total - offset - len(page)
        if remaining > 0:
            lines.append(f"\n... 還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
