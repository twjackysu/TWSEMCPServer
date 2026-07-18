"""TWSE per-stock foreign/mainland-China (外資及陸資) shareholding ratio history."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, DEFAULT_DISPLAY_LIMIT

MI_QFIIS_URL = "https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE foreign holdings history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_foreign_holdings_history(date: str, stock_no: str = "", name: str = "",
                                      limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢指定日期全部上市股票的外資及陸資持股比率。
        與 get_foreign_investment_by_industry（產業匯總）、get_top_foreign_holdings（前20名排行）
        不同：這兩者都只有最新一日、且無法指定個股；此工具可查詢「任意過去日期＋任意個股」的
        外資持股狀況，適合追蹤外資持股比率隨時間的變化。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260610"（需為交易日）
            stock_no: 股票代號（選填），指定則只回傳該股票
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每支股票的代號、名稱、發行股數、外資及陸資尚可投資股數/比率、全體外資及陸資持股數/比率
        """
        resp = _client.fetch_json(
            MI_QFIIS_URL,
            params={"response": "json", "date": date, "selectType": "ALLBUT0999"},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的外資及陸資持股資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的外資及陸資持股資料"

        if stock_no:
            data = [row for row in data if row[0].strip() == stock_no]
            if not data:
                return f"查無股票代號 {stock_no} 在 {date} 的外資及陸資持股資料"
        if name:
            data = [row for row in data if name in row[1]]
            if not data:
                return f"查無名稱包含「{name}」的股票在 {date} 的外資及陸資持股資料"

        total = len(data)
        page_data = data[offset:offset + limit]
        end = min(offset + limit, total)

        title = resp.get("title", f"{date} 外資及陸資投資持股統計")
        header = f"【{title}】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for row in page_data:
            # row: 證券代號,證券名稱,國際證券編碼,發行股數,外資及陸資尚可投資股數,
            #      全體外資及陸資持有股數,外資及陸資尚可投資比率,全體外資及陸資持股比率, ...
            code, sname = row[0], row[1]
            issued = row[3]
            remain_shares, held_shares = row[4], row[5]
            remain_pct, held_pct = row[6], row[7]
            lines.append(
                f"{code} {sname} | 外資持股比率:{held_pct}% | 尚可投資比率:{remain_pct}% | "
                f"持有股數:{held_shares} | 發行股數:{issued}"
            )

        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")

        return "\n".join(lines)
