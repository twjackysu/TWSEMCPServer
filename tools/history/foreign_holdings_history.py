"""Foreign/mainland-China (外資及陸資) shareholding of every listed stock, latest or any past date.

Replaces the OpenAPI /fund/MI_QFIIS_sort_20 tool (get_top_foreign_holdings): on 2026-09-29
its top 20 were exactly this endpoint's rows sorted by 全體外資及陸資持股比率, with the same
ratios, limits and share counts, and it could neither pick a date nor look up one stock.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT, format_list_response

MI_QFIIS_URL = "https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS"

# row: 證券代號,證券名稱,國際證券編碼,發行股數,外資及陸資尚可投資股數,全體外資及陸資持有股數,
#      外資及陸資尚可投資比率,全體外資及陸資持股比率,外資及陸資共用法令投資上限比率, ...
COL_HELD_RATIO = 7
SORT_OPTIONS = ("code", "ratio")


def _ratio(row) -> float:
    try:
        return float(str(row[COL_HELD_RATIO]).replace(",", ""))
    except (ValueError, IndexError):
        return -1.0


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE foreign holdings tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_foreign_holdings(date: str = "", stock_no: str = "", name: str = "", sort_by: str = "code",
                             limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市股票外資及陸資持股比率：預設最新交易日，也可指定任意過去日期，適合追蹤外資持股變化。
        sort_by="ratio" 可依外資持股比率由高到低排行（例如 limit=20 即外資持股前 20 名）。
        產業別匯總請用 get_foreign_investment_by_industry。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            sort_by: "code"＝依證券代號（預設）；"ratio"＝依全體外資及陸資持股比率由高到低
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的代號、名稱、全體外資及陸資持股比率、尚可投資比率、投資上限比率、持有股數、發行股數
        """
        if sort_by not in SORT_OPTIONS:
            return f"sort_by 只能是 {', '.join(SORT_OPTIONS)}"
        params = {"response": "json", "selectType": "ALLBUT0999"}
        if date:
            params["date"] = date
        resp = _client.fetch_json(MI_QFIIS_URL, params=params)
        label = date or "最新交易日"

        if not resp or resp.get("stat") != "OK":
            return f"查無 {label} 的外資及陸資持股資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {label} 的外資及陸資持股資料"
        served = resp.get("date") or label

        if stock_no:
            data = [row for row in data if row[0].strip() == stock_no.strip()]
            if not data:
                return f"查無股票代號 {stock_no} 在 {served} 的外資及陸資持股資料"
        if name:
            data = [row for row in data if name in row[1]]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {served} 的外資及陸資持股資料"
        if sort_by == "ratio":
            data = sorted(data, key=_ratio, reverse=True)

        def fmt(row):
            code, sname = row[0], row[1]
            issued = row[3]
            held_shares = row[5]
            remain_pct, held_pct, limit_pct = row[6], row[7], row[8]
            return (
                f"{code} {sname} | 外資持股比率:{held_pct}% | 尚可投資比率:{remain_pct}% | "
                f"投資上限:{limit_pct}% | 持有股數:{held_shares} | 發行股數:{issued}\n"
            )

        order = "，依持股比率由高到低" if sort_by == "ratio" else ""
        return format_list_response(data, f" {served} 上市股票外資及陸資持股{order}", fmt, limit, offset)
