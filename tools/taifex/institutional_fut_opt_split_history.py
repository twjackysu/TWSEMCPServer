"""TAIFEX 三大法人期貨/選擇權二類分計 history (multi-day download, futures vs options side by side)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS
from .futures_daily_history import parse_yyyymmdd, decode_and_parse_csv

# Distinct from get_institutional_total_history (futures+options combined into one
# number) and get_institutional_traders_by_futures_history (futures only): this endpoint
# reports futures and options side by side per identity, so the two can be compared
# directly. openapi.taifex.com.tw has no equivalent at all — this data isn't exposed
# there under any endpoint. No server-enforced span cap observed (tested a clean 3-month
# pull), capped client-side at 92 days. Retention verified to run out between 2023/06 and
# 2023/09.
FUT_AND_OPT_DATE_DOWN_URL = "https://www.taifex.com.tw/cht/3/futAndOptDateDown"

MAX_SPAN_DAYS = 92


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TAIFEX institutional futures-vs-options split history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_institutional_fut_opt_split_history(start_date: str, end_date: str) -> str:
        """查詢三大法人期貨與選擇權分計交易歷史（期貨、選擇權並列顯示，可回溯查詢）。
        與 get_institutional_total_history（期貨+選擇權合計成一個數字）不同，此工具將期貨與
        選擇權的多空交易口數、契約金額、未平倉分開列出，方便比較兩者布局是否一致。
        此資料在 openapi.taifex.com.tw 完全沒有對應端點。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260401"
            end_date: 結束日期，格式 YYYYMMDD。與 start_date 區間不可超過 92 天

        Returns:
            區間內每個交易日、每個身份別（自營商/投信/外資及陸資）的期貨與選擇權各自多空
            交易口數、契約金額（千元）、未平倉口數
        """
        try:
            start_dt = parse_yyyymmdd(start_date)
            end_dt = parse_yyyymmdd(end_date)
        except ValueError:
            return f"日期格式錯誤，請使用 YYYYMMDD 格式（例如 20260401），收到：start_date={start_date}, end_date={end_date}"

        if start_dt > end_dt:
            return f"起始日期 {start_date} 不可晚於結束日期 {end_date}"
        if (end_dt - start_dt).days > MAX_SPAN_DAYS:
            return f"查詢區間不可超過 {MAX_SPAN_DAYS} 天（收到 {(end_dt - start_dt).days} 天），請縮小 start_date～end_date 範圍後重試"

        body = _client.fetch_bytes(
            FUT_AND_OPT_DATE_DOWN_URL,
            method="POST",
            headers=TAIFEX_HEADERS,
            data={
                "queryStartDate": start_dt.strftime("%Y/%m/%d"),
                "queryEndDate": end_dt.strftime("%Y/%m/%d"),
            },
        )
        parsed = decode_and_parse_csv(body)
        if parsed is None:
            return (
                f"查無 {start_date}～{end_date} 的三大法人期貨/選擇權分計資料，"
                f"日期區間可能超出資料保存範圍（約近 3 年內）或格式有誤"
            )

        _header, data_rows = parsed
        lines = [
            f"【三大法人期貨/選擇權分計歷史】區間:{start_date}~{end_date}（共 {len(data_rows)} 筆）\n"
        ]
        for r in data_rows:
            date, identity = r[0], r[1]
            # 偶數 index = 期貨欄位, 奇數 index = 選擇權欄位
            fut_long_vol, opt_long_vol = r[2], r[3]
            fut_short_vol, opt_short_vol = r[6], r[7]
            fut_net_vol, opt_net_vol = r[10], r[11]
            fut_oi_long, opt_oi_long = r[14], r[15]
            fut_oi_short, opt_oi_short = r[18], r[19]
            fut_oi_net, opt_oi_net = r[22], r[23]
            lines.append(
                f"{date} | {identity}\n"
                f"  期貨: 交易 多{fut_long_vol}/空{fut_short_vol}/淨{fut_net_vol} | "
                f"未平倉 多{fut_oi_long}/空{fut_oi_short}/淨{fut_oi_net}\n"
                f"  選擇權: 交易 多{opt_long_vol}/空{opt_short_vol}/淨{opt_net_vol} | "
                f"未平倉 多{opt_oi_long}/空{opt_oi_short}/淨{opt_oi_net}"
            )

        return "\n".join(lines)
