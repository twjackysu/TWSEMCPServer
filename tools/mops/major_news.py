"""Material information (重大訊息) from MOPS: a company's announcements over a year, or the
whole market's announcements on one day, with the full text for a company's announcements.

Replaces the OpenAPI /opendata/t187ap04_L tool. On 2026-09-29 all 115 of its announcements
(listed companies, latest day only) were among MOPS t05st02's 205 for that day, which also
covers OTC, emerging and public companies and any past date. t187ap04_L carried each
announcement's full text inline; MOPS lists subjects and serves the text per announcement
(t05st01_detail / t05st02_detail), so this tool fetches it for a named company's page.
"""

from datetime import timedelta
from typing import Literal, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, truncate, Page
from toolkit import Limit, Offset, handle_api_errors
from utils.mops import mops_post, to_roc_year
from utils.date_helper import taipei_today

Market = Literal["", "sii", "otc", "rotc", "pub"]  # "" (every market) or a key of MARKET_LABELS
MARKET_LABELS = {"sii": "上市", "otc": "上櫃", "rotc": "興櫃", "pub": "公發"}
# Each full text costs one MOPS request, so a company page shows at most this many.
MAX_DETAILED = 10
LATEST_LOOKBACK_DAYS = 10
MAX_TEXT_CHARS = 1500


def _one_line(text) -> str:
    """Subjects often contain line breaks; keep each announcement on one line."""
    return " ".join(str(text).split())


def _roc_day(date: str) -> Optional[str]:
    """YYYYMMDD → ROC "YYY/MM/DD" as MOPS prints 發言日期, or None if malformed."""
    if len(date) != 8 or not date.isdigit():
        return None
    return f"{int(date[:4]) - 1911}/{date[4:6]}/{date[6:]}"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _detail(link) -> str:
        """Full text of one announcement from its 詳細資料 link ({apiName, parameters})."""
        if not isinstance(link, dict) or not link.get("apiName"):
            return ""
        result = mops_post(_client, link["apiName"], link.get("parameters") or {})
        rows = (result or {}).get("data") or []
        if not rows:
            return ""
        # row: 序號,發言日期,發言時間,發言人,發言人職稱,發言人電話,主旨,符合條款,事實發生日,說明
        r = rows[0]
        return (
            f"  符合條款:{r[7]} | 事實發生日:{r[8]} | 發言人:{r[3].strip()}（{r[4].strip()}）\n"
            f"  說明:{truncate(str(r[9]).strip(), MAX_TEXT_CHARS)}"
        )

    def _company(code: str, date: str, year: str, limit: int, offset: int) -> str:
        roc_day = _roc_day(date) if date else None
        if date and roc_day is None:
            raise ToolError("日期格式錯誤，請使用 YYYYMMDD，例如 \"20260929\"")
        roc_year = to_roc_year(year) if year else (int(roc_day[:3]) if roc_day else taipei_today().year - 1911)
        result = mops_post(_client, "t05st01", {
            "companyId": code, "year": str(roc_year), "month": "all", "firstDay": "", "lastDay": "",
        })
        # row: 公司代號,公司名稱,發言日期,發言時間,主旨,詳細資料
        rows = (result or {}).get("data") or []
        if roc_day:
            rows = [r for r in rows if r[2] == roc_day]
        if not rows:
            scope = roc_day or f"民國{roc_year}年"
            return f"查無 {code} 在 {scope} 的重大訊息"

        rows = sorted(rows, key=lambda r: (r[2], r[3]), reverse=True)
        # Each full text costs a MOPS request, so a page holds at most MAX_DETAILED.
        paged = Page(min(limit, MAX_DETAILED), offset).take(rows)
        if paged.past_end:
            return paged.out_of_range(f"{code} 的重大訊息")
        name = result.get("companyAbbreviation") or rows[0][1]
        span = f"，{paged.span('則')}" if paged.span("則") else ""
        lines = [f"【{name}({code}) 重大訊息 民國{roc_year}年{('（' + roc_day + '）') if roc_day else ''}】"
                 f"（共 {paged.total} 則，由新到舊{span}，每頁最多 {MAX_DETAILED} 則含全文）\n"]
        for r in paged.rows:
            lines.append(f"{r[2]} {r[3]} | {_one_line(r[4])}")
            detail = _detail(r[5] if len(r) > 5 else None)
            if detail:
                lines.append(detail)
        if paged.more("則"):
            lines.append("\n" + paged.more("則"))
        return "\n".join(lines)

    def _market(date: str, market: str, limit: int, offset: int) -> str:
        if date:
            if _roc_day(date) is None:
                raise ToolError("日期格式錯誤，請使用 YYYYMMDD，例如 \"20260929\"")
            days = [date]
        else:
            today = taipei_today()
            days = [f"{today - timedelta(days=i):%Y%m%d}" for i in range(LATEST_LOOKBACK_DAYS)]

        rows, served = [], ""
        for day in days:
            result = mops_post(_client, "t05st02", {"year": str(int(day[:4]) - 1911), "month": day[4:6], "day": day[6:]})
            rows = (result or {}).get("data") or []
            if rows:
                served = day
                break
        if not rows:
            return f"查無 {date or '最近'} 的重大訊息"

        # row: 發言日期,發言時間,公司代號,公司名稱,主旨,詳細資料({parameters.marketKind})
        def kind(r):
            link = r[5] if len(r) > 5 and isinstance(r[5], dict) else {}
            return (link.get("parameters") or {}).get("marketKind", "")

        if market:
            rows = [r for r in rows if kind(r) == market]
        paged = Page(limit, offset).take(rows)
        if paged.past_end:
            return paged.out_of_range(f"{served} 的重大訊息")
        span = f"，{paged.span('則')}" if paged.span("則") else ""
        lines = [f"【查詢日 {served} 全市場重大訊息】（共 {paged.total} 則{span}；指定 code 可看各則全文）\n"]
        for r in paged.rows:
            lines.append(f"{r[0]} {r[1]} | {MARKET_LABELS.get(kind(r), kind(r))} {r[2]} {r[3]} | {_one_line(r[4])}")
        if paged.more("則"):
            lines.append("\n" + paged.more("則"))
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_company_major_news(code: str = "", date: str = "", year: str = "", market: Market = "",
                               limit: Limit = 50, offset: Offset = 0) -> str:
        """查詢重大訊息（公開資訊觀測站），上市、上櫃、興櫃、公發公司皆可。
        指定 code：列出該公司某年度的重大訊息（由新到舊，每則附符合條款、事實發生日與說明全文）。
        不指定 code：列出某一天全市場的重大訊息主旨（預設最近一個有公告的日子）。

        回傳：發言日期與時間、公司、主旨；指定 code 時另含符合條款、事實發生日、發言人與說明全文

        Args:
            code: 股票代號（選填），例如 "2330"
            date: 發言日期 YYYYMMDD（選填）。搭配 code 時只看該日；不搭配 code 時查該日全市場
            year: 年度，西元或民國（選填，僅搭配 code；預設今年）
            market: 市場別篩選（選填，僅全市場模式）：sii 上市、otc 上櫃、rotc 興櫃、pub 公發
            limit: 回傳則數上限（預設 50；指定 code 時每頁最多 10 則，因每則全文需另外查詢）
            offset: 跳過前 N 則（預設 0，搭配 limit 分頁）
        """
        if code.strip():
            return _company(code.strip(), date.strip(), year.strip(), limit, offset)
        return _market(date.strip(), market, limit, offset)
