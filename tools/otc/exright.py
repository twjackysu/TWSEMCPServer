"""OTC (上櫃) ex-rights / ex-dividend results (除權除息計算結果), today or any date range.

Source: www.tpex.org.tw website JSON bulletin/exDailyQ. It replaces the openapi
tpex_exright_daily tool: on 2026-09-30 the openapi endpoint's only row (8440) matched this
endpoint's row for that day in all 18 value columns, and this endpoint also lists the next
day's pre-announced results and accepts any past range (e.g. 2024-01～2026-09 in one call).
The listed-market counterpart is get_exright_results_history (TWSE TWT49U).
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_list_response, DEFAULT_DISPLAY_LIMIT
from .history import TPEX_WWW, first_table, to_tpex_date

EX_DAILY_Q_URL = f"{TPEX_WWW}/bulletin/exDailyQ"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register OTC ex-rights/dividends tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_otc_exright(start_date: str = "", end_date: str = "", stock_no: str = "",
                        limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上櫃股票除權除息計算結果：預設今天與下一個交易日，也可指定任意過去區間。
        可用於還原權息、計算填權息。上市股票請用 get_exright_results_history。

        Args:
            start_date: 起始日期 YYYYMMDD（選填，留空＝今天起）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）
            stock_no: 股票代號（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            除權息日期、代號、名稱、類型、除權息前收盤價、參考價、權值、息值、漲跌停價、
            開始交易基準價、現金股利、每仟股無償配股、現金增資股數與認購價
        """
        params = {"response": "json"}
        if start_date or end_date:
            start = to_tpex_date(start_date or end_date)
            end = to_tpex_date(end_date or start_date)
            if not start or not end:
                return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260701\""
            params.update(startDate=start, endDate=end)
        resp = _client.fetch_json(EX_DAILY_Q_URL, params=params)
        served = str((resp or {}).get("date", "")).replace("~", "～")
        rows = first_table(resp).get("data") or []
        rows = [[c.strip() if isinstance(c, str) else c for c in r] for r in rows]
        if not rows:
            return f"查無 {served or '指定期間'} 的上櫃除權息資料"
        # 代號在 row[1]（row[0] 是日期）
        rows = [r for r in rows if not stock_no or r[1] == stock_no.strip()]

        def fmt(r):
            # r: 除權息日期,代號,名稱,除權息前收盤價,除權息參考價,權值,息值,權值+息值,權/息,漲停價,跌停價,
            #    開始交易基準價,減除股利參考價,現金股利,每仟股無償配股,現金增資股數,現金增資認購價,...
            capital = f" | 現增:{r[15]}股@{r[16]}" if str(r[15]) not in ("0", "") else ""
            return (
                f"{r[0]} | {r[1]} {r[2]} | {r[8]} | 前收:{r[3]} 參考價:{r[4]}（權值 {r[5]} 息值 {r[6]}）| "
                f"現金股利:{r[13]} 每仟股配股:{r[14]} | 漲停:{r[9]} 跌停:{r[10]} 開始交易基準價:{r[11]}{capital}\n"
            )

        return format_list_response(rows, f" {served} 上櫃除權除息計算結果", fmt, limit, offset)

