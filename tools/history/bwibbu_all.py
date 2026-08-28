"""Market-wide valuation ratios (P/E, dividend yield, P/B) from legacy TWSE endpoint."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

# rwd/zh/afterTrading/BWIBBU_d honours the `date` parameter and echoes it back.
# The older /exchangeReport/BWIBBU_ALL silently ignores `date` entirely — every
# request returns the latest trading day — so it cannot serve historical queries.
BWIBBU_D_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d"

# Column order of BWIBBU_d's `data` rows, per its `fields` array:
# ['證券代號', '證券名稱', '收盤價', '殖利率(%)', '股利年度', '本益比', '股價淨值比', '財報年/季']
COL_CODE, COL_NAME, COL_CLOSE, COL_YIELD, COL_PE, COL_PB = 0, 1, 2, 3, 5, 6


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market valuation tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_market_valuation_by_date(date: str, stock_no: str = "",
                                     limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢全市場上市股票的本益比（P/E）、殖利率、股價淨值比（P/B）。
        適合用於篩選低估值個股或比較產業估值水位。
        可指定特定股票代號只查單一個股。

        Args:
            date: 查詢日期 YYYYMMDD，回傳該日的估值資料
            stock_no: 股票代號（選填），若指定則只回傳該股票的估值資料
            limit: 回傳筆數上限（預設 50）。全市場逾 1000 檔，未分頁的完整輸出逾 60KB
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的代號、名稱、收盤價、本益比、殖利率(%)、股價淨值比
        """
        resp = _client.fetch_json(
            BWIBBU_D_URL,
            params={"response": "json", "date": date, "selectType": "ALL"},
        )

        if not resp or resp.get("stat") != "OK":
            reason = (resp or {}).get("stat") or "請確認該日期為交易日（非假日或週末）"
            return f"查無 {date} 的估值資料：{reason}"

        # The endpoint echoes back the date it actually served. Never relabel a
        # different day's data with the requested date.
        served_date = resp.get("date") or date
        if served_date != date:
            return (
                f"查無 {date} 的估值資料，來源實際回傳的是 {served_date} 的資料，"
                f"請改用 {served_date} 查詢，或確認 {date} 為交易日。"
            )

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的估值資料"

        # Filter by stock_no if specified
        if stock_no:
            data = [row for row in data if row[COL_CODE].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的估值資料"

        total = len(data)
        page = data[offset:offset + limit]
        if not page:
            return f"offset={offset} 已超出範圍，{date} 的估值資料共 {total} 筆"

        title = resp.get("title") or f"全市場估值資料 - {date}"
        page_note = f"，顯示第 {offset + 1}–{offset + len(page)} 筆" if total > len(page) else ""
        lines = [f"【{title}】（共 {total} 筆{page_note}）\n"]

        for row in page:
            code = row[COL_CODE].strip()
            name = row[COL_NAME].strip()
            close = row[COL_CLOSE] or "-"
            dy = row[COL_YIELD] or "-"
            pe = row[COL_PE] or "-"
            pb = row[COL_PB] or "-"
            lines.append(
                f"{code} {name} | 收盤價: {close} | 本益比: {pe} | 殖利率: {dy}% | 股價淨值比: {pb}"
            )

        remaining = total - offset - len(page)
        if remaining > 0:
            lines.append(f"\n... 還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
