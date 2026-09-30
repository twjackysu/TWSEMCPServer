"""Per-company monthly revenue (每月營業收入) from MOPS t05st10_ifrs, latest or any range.

Replaces the OpenAPI t187ap05_L / t187ap05_P tools, which only had the latest month and
needed separate endpoints for listed and public companies. MOPS answers one month per
request, so a range is fetched month by month; the span is capped to keep a single tool
call to a handful of seconds under the client's rate limit.
"""

from datetime import date
from typing import List, Optional, Tuple
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.mops import mops_post

MAX_MONTHS = 12

# data 的第一組 [項目, 值] 是當月營收；月增率由相鄰月份的這個值算出。
# tests/e2e/test_mops_api.py 驗證此標籤仍存在。
CURRENT_MONTH_LABEL = "本月"


def parse_month_range(start_month: str, end_month: str) -> Tuple[Optional[List[Tuple[int, int]]], Optional[str]]:
    """Expand "YYYYMM"～"YYYYMM" (western calendar) into [(year, month), ...].

    Returns (months, None) or (None, error message).
    """
    try:
        sy, sm = int(start_month[:4]), int(start_month[4:6])
        ey, em = int(end_month[:4]), int(end_month[4:6])
        if len(start_month) != 6 or len(end_month) != 6:
            raise ValueError
        date(sy, sm, 1), date(ey, em, 1)
    except (ValueError, TypeError):
        return None, "月份格式錯誤，請使用 YYYYMM（西元），例如 \"202601\""

    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    if not months:
        return None, "起始月份不可晚於結束月份"
    if len(months) > MAX_MONTHS:
        return None, f"查詢區間最多 {MAX_MONTHS} 個月（目前 {len(months)} 個月），請縮小範圍"
    return months, None


def previous_month(y: int, m: int) -> Tuple[int, int]:
    return (y - 1, 12) if m == 1 else (y, m - 1)


def current_month_revenue(result: Optional[dict]) -> Optional[float]:
    """The 本月 revenue of a t05st10_ifrs result as a number, or None."""
    for row in (result or {}).get("data") or []:
        if isinstance(row, list) and len(row) >= 2 and str(row[0]).strip() == CURRENT_MONTH_LABEL:
            try:
                return float(str(row[1]).replace(",", ""))
            except ValueError:
                return None
    return None


def format_month(label: str, result: Optional[dict], prev_result: Optional[dict]) -> str:
    """One output line: MOPS's own [項目, 值] pairs, plus 月增率 when the prior month is known."""
    if not result or not result.get("data"):
        return f"{label}: 尚未公告或查無資料"
    # 兩組「增減金額／增減百分比」分別屬於單月與累計，依原順序輸出即可辨識
    pairs = [
        f"{str(row[0]).strip()}:{str(row[1]).strip() or '-'}"
        for row in result["data"] if isinstance(row, list) and len(row) >= 2
    ]
    cur, prev = current_month_revenue(result), current_month_revenue(prev_result)
    if cur is not None and prev:
        pairs.insert(1, f"月增率:{(cur - prev) / prev * 100:.2f}")
    return f"{label} | " + " | ".join(pairs)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS monthly revenue tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _fetch(code: str, y: Optional[int] = None, m: Optional[int] = None) -> Optional[dict]:
        if y is None:
            # 最新月份：dataType=1 仍須帶空的 year/month
            body = {"companyId": code, "dataType": "1", "year": "", "month": "", "subsidiaryCompanyId": ""}
        else:
            body = {"companyId": code, "dataType": "2", "year": str(y - 1911), "month": str(m),
                    "subsidiaryCompanyId": ""}
        return mops_post(_client, "t05st10_ifrs", body)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_monthly_revenue(code: str, start_month: str = "", end_month: str = "") -> str:
        """查詢公司月營收（公開資訊觀測站）：預設最新公告月份，也可查任意過去月份區間。
        上市、上櫃、興櫃、公開發行公司皆可。每月含當月營收、月增率、去年同期、年增率、
        今年累計與累計年增率，以及公司對大幅變動的說明。

        Args:
            code: 股票代號，例如 "2330"
            start_month: 起始月份，西元 YYYYMM，例如 "202601"；留空＝最新公告月份（附上前一個月對照）
            end_month: 結束月份，西元 YYYYMM（選填，預設同 start_month）。區間最多 12 個月

        Returns:
            每個月份的營收數據（單位：新台幣仟元）。尚未公告的月份會標示「尚未公告」
        """
        code = code.strip()
        if start_month.strip():
            months, error = parse_month_range(start_month.strip(), (end_month or start_month).strip())
            if error:
                return error
            # 多抓區間前一個月，讓第一個月也有月增率
            results = {ym: _fetch(code, *ym) for ym in [previous_month(*months[0])] + months}
        else:
            latest = _fetch(code)
            if not latest or not latest.get("yymm"):
                return f"查無 {code} 的月營收資料（代號可能有誤）"
            roc_ym = str(latest["yymm"])
            ym = (int(roc_ym[:-2]) + 1911, int(roc_ym[-2:]))
            prev = previous_month(*ym)
            months = [prev, ym]
            results = {prev: _fetch(code, *prev), ym: latest}

        name = next((r.get("companyAbbreviation") for r in results.values() if r), "") or code
        lines = [
            f"【{name}({code}) 月營收 {months[0][0]}-{months[0][1]:02d}～{months[-1][0]}-{months[-1][1]:02d}】"
            "（單位：新台幣仟元；百分比為 %）"
        ]
        for ym in months:
            lines.append(format_month(f"{ym[0]}-{ym[1]:02d}", results[ym], results.get(previous_month(*ym))))
        return "\n".join(lines)
