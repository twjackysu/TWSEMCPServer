"""Per-company monthly revenue (每月營業收入) from MOPS t05st10_ifrs, latest or any range.

Replaces the OpenAPI t187ap05_L / t187ap05_P tools, which only had the latest month and
needed separate endpoints for listed and public companies. MOPS answers one month per
request, so a range is fetched month by month; the span is capped to keep a single tool
call to a handful of seconds under the client's rate limit. Read through ``sources.mops.monthly_revenue``.
"""

from datetime import date
from typing import List, Optional, Tuple, Union
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.mops.monthly_revenue import MonthlyRevenue, monthly_revenue
from utils import TWSEAPIClient
from toolkit import handle_api_errors

MAX_MONTHS = 12


def parse_month_range(start_month: str, end_month: str) -> Union[List[Tuple[int, int]], str]:
    """Expand "YYYYMM"～"YYYYMM" (western calendar) into [(year, month), ...].

    Returns the months, or an error message.
    """
    try:
        sy, sm = int(start_month[:4]), int(start_month[4:6])
        ey, em = int(end_month[:4]), int(end_month[4:6])
        if len(start_month) != 6 or len(end_month) != 6:
            raise ValueError
        date(sy, sm, 1)
        date(ey, em, 1)
    except (ValueError, TypeError):
        return "月份格式錯誤，請使用 YYYYMM（西元），例如 \"202601\""

    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    if not months:
        return "起始月份不可晚於結束月份"
    if len(months) > MAX_MONTHS:
        return f"查詢區間最多 {MAX_MONTHS} 個月（目前 {len(months)} 個月），請縮小範圍"
    return months


def previous_month(y: int, m: int) -> Tuple[int, int]:
    return (y - 1, 12) if m == 1 else (y, m - 1)


def format_month(label: str, revenue: Optional[MonthlyRevenue], prev: Optional[MonthlyRevenue]) -> str:
    """One output line: MOPS's own 項目:值 pairs, plus 月增率 when the prior month is known."""
    if revenue is None or not revenue.items:
        return f"{label}: 尚未公告或查無資料"
    # 兩組「增減金額／增減百分比」分別屬於單月與累計，依原順序輸出即可辨識
    pairs = [f"{item.label}:{item.value or '-'}" for item in revenue.items]
    cur, before = revenue.current, prev.current if prev else None
    if cur is not None and before:
        pairs.insert(1, f"月增率:{(cur - before) / before * 100:.2f}")
    return f"{label} | " + " | ".join(pairs)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS monthly revenue tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_monthly_revenue(code: str, start_month: str = "", end_month: str = "") -> str:
        """查詢公司月營收（公開資訊觀測站）：預設最新公告月份，也可查任意過去月份區間。
        上市、上櫃、興櫃、公開發行公司皆可。每月含當月營收、月增率（MoM）、去年同期、年增率（YoY）、
        今年累計與累計年增率，以及公司對大幅變動的說明。

        回傳：每個月份的營收數據（單位：新台幣仟元）。尚未公告的月份會標示「尚未公告」

        Args:
            code: 股票代號，例如 "2330"
            start_month: 起始月份，西元 YYYYMM，例如 "202601"；留空＝最新公告月份（附上前一個月對照）
            end_month: 結束月份，西元 YYYYMM（選填，預設同 start_month）。區間最多 12 個月
        """
        code = code.strip()
        if start_month.strip():
            months = parse_month_range(start_month.strip(), (end_month or start_month).strip())
            if isinstance(months, str):
                raise ToolError(months)
            # 多抓區間前一個月，讓第一個月也有月增率
            results = {ym: monthly_revenue(_client, code, *ym) for ym in [previous_month(*months[0])] + months}
        else:
            latest = monthly_revenue(_client, code)  # 最新月份（dataType=1）
            if latest is None or latest.period is None:
                return f"查無 {code} 的月營收資料（代號可能有誤）"
            ym = latest.period
            prev = previous_month(*ym)
            months = [prev, ym]
            results = {prev: monthly_revenue(_client, code, *prev), ym: latest}

        name = next((r.name for r in results.values() if r), "") or code
        lines = [
            f"【{name}({code}) 月營收 {months[0][0]}-{months[0][1]:02d}～{months[-1][0]}-{months[-1][1]:02d}】"
            "（單位：新台幣仟元；百分比為 %）"
        ]
        for ym in months:
            lines.append(format_month(f"{ym[0]}-{ym[1]:02d}", results[ym], results.get(previous_month(*ym))))
        return "\n".join(lines)
