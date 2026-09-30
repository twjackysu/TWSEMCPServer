"""Per-company monthly revenue history (每月營業收入) from MOPS t05st10_ifrs.

get_company_monthly_revenue (OpenAPI t187ap05_L) only has the latest month. MOPS answers
one month per request, so a range is fetched month by month; the span is capped to keep a
single tool call to a handful of seconds under the client's rate limit.
"""

from datetime import date
from typing import List, Optional, Tuple
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.mops import mops_post

MAX_MONTHS = 12


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


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS monthly revenue history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_monthly_revenue_history(code: str, start_month: str, end_month: str = "") -> str:
        """查詢上市櫃公司「多個月份」的月營收歷史（公開資訊觀測站）。
        與 get_company_monthly_revenue（OpenAPI，僅最新一個月）不同，可回溯查詢任意過去月份，
        每月含當月營收、去年同期、年增率、今年累計與累計年增率，以及公司對大幅變動的說明。

        Args:
            code: 股票代號，例如 "2330"（上市、上櫃、興櫃皆可）
            start_month: 起始月份，西元 YYYYMM，例如 "202601"
            end_month: 結束月份，西元 YYYYMM（選填，預設同 start_month）。區間最多 12 個月

        Returns:
            每個月份的營收數據（單位：新台幣仟元）。尚未公告的月份會標示「尚未公告」
        """
        code = code.strip()
        months, error = parse_month_range(start_month.strip(), (end_month or start_month).strip())
        if error:
            return error

        name = ""
        blocks = []
        for y, m in months:
            result = mops_post(_client, "t05st10_ifrs", {
                "companyId": code,
                "dataType": "2",
                "year": str(y - 1911),
                "month": str(m),
                "subsidiaryCompanyId": "",
            })
            label = f"{y}-{m:02d}"
            if not result or not result.get("data"):
                blocks.append(f"{label}: 尚未公告或查無資料")
                continue
            name = name or result.get("companyAbbreviation", "")
            # data 是 [項目, 值] 配對；兩組「增減金額／增減百分比」分別屬於單月與累計，
            # 依原順序輸出即可辨識，不另外寫死項目名稱。
            pairs = [
                f"{str(row[0]).strip()}:{str(row[1]).strip() or '-'}"
                for row in result["data"] if isinstance(row, list) and len(row) >= 2
            ]
            blocks.append(f"{label} | " + " | ".join(pairs))

        header = f"【{name or code}({code}) 月營收歷史 {months[0][0]}-{months[0][1]:02d}～{months[-1][0]}-{months[-1][1]:02d}】（單位：新台幣仟元）\n"
        return header + "\n".join(blocks)
