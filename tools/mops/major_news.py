"""Material information (重大訊息) from MOPS: a company's announcements over a year, or the
whole market's announcements on one day, with the full text for a company's announcements.

Replaces the OpenAPI /opendata/t187ap04_L tool. On 2026-09-29 all 115 of its announcements
(listed companies, latest day only) were among MOPS t05st02's 205 for that day, which also
covers OTC, emerging and public companies and any past date. t187ap04_L carried each
announcement's full text inline; MOPS lists subjects and serves the text per announcement
(t05st01_detail / t05st02_detail), so this tool fetches it for a named company's page. All three are
read through ``sources.mops.major_news``.
"""

from datetime import timedelta
from typing import Literal, Optional
from fastmcp import FastMCP
from sources.mops.major_news import NewsLink, company_news, market_news, news_detail
from utils import TWSEAPIClient, truncate, Page
from toolkit import Limit, Offset, TradingDate, handle_api_errors
from utils.mops import to_roc_year
from utils.date_helper import roc_date, roc_year_of, taipei_today

Market = Literal["", "sii", "otc", "rotc", "pub"]  # "" (every market) or a key of MARKET_LABELS
MARKET_LABELS = {"sii": "上市", "otc": "上櫃", "rotc": "興櫃", "pub": "公發"}
# Each full text costs one MOPS request, so a company page shows at most this many.
MAX_DETAILED = 10
LATEST_LOOKBACK_DAYS = 10
MAX_TEXT_CHARS = 1500


def _one_line(text) -> str:
    """Subjects often contain line breaks; keep each announcement on one line."""
    return " ".join(str(text).split())


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _detail(link: Optional[NewsLink]) -> str:
        """Full text of one announcement from its 詳細資料 link."""
        d = news_detail(_client, link) if link else None
        if d is None:
            return ""
        return (
            f"  符合條款:{d.clause} | 事實發生日:{d.fact_date} | 發言人:{d.spokesperson}（{d.spokesperson_title}）\n"
            f"  說明:{truncate(d.text, MAX_TEXT_CHARS)}"
        )

    def _company(code: str, date: str, year: str, limit: int, offset: int) -> str:
        roc_day = roc_date(date) if date else None  # as MOPS prints 發言日期: 115/09/10
        roc_year = to_roc_year(year) if year else (roc_year_of(date) if date else taipei_today().year - 1911)
        news = company_news(_client, code, roc_year)
        rows = news.announcements if news else []
        if roc_day:
            rows = [a for a in rows if a.date == roc_day]
        if not rows:
            scope = roc_day or f"民國{roc_year}年"
            return f"查無 {code} 在 {scope} 的重大訊息"

        rows = sorted(rows, key=lambda a: (a.date, a.time), reverse=True)
        # Each full text costs a MOPS request, so a page holds at most MAX_DETAILED.
        paged = Page(min(limit, MAX_DETAILED), offset).take(rows)
        if paged.past_end:
            return paged.out_of_range(f"{code} 的重大訊息")
        name = (news.name if news else "") or rows[0].name
        span = f"，{paged.span('則')}" if paged.span("則") else ""
        lines = [f"【{name}({code}) 重大訊息 民國{roc_year}年{('（' + roc_day + '）') if roc_day else ''}】"
                 f"（共 {paged.total} 則，由新到舊{span}，每頁最多 {MAX_DETAILED} 則含全文）\n"]
        for a in paged.rows:
            lines.append(f"{a.date} {a.time} | {_one_line(a.subject)}")
            detail = _detail(a.link)
            if detail:
                lines.append(detail)
        if paged.more("則"):
            lines.append("\n" + paged.more("則"))
        return "\n".join(lines)

    def _market(date: str, market: str, limit: int, offset: int) -> str:
        if date:
            days = [date]
        else:
            today = taipei_today()
            days = [f"{today - timedelta(days=i):%Y%m%d}" for i in range(LATEST_LOOKBACK_DAYS)]

        rows, served = [], ""
        for day in days:
            rows = market_news(_client, day)
            if rows:
                served = day
                break
        if not rows:
            return f"查無 {date or '最近'} 的重大訊息"

        if market:
            rows = [a for a in rows if a.market == market]
        paged = Page(limit, offset).take(rows)
        if paged.past_end:
            return paged.out_of_range(f"{served} 的重大訊息")
        span = f"，{paged.span('則')}" if paged.span("則") else ""
        lines = [f"【查詢日 {served} 全市場重大訊息】（共 {paged.total} 則{span}；指定 code 可看各則全文）\n"]
        for a in paged.rows:
            lines.append(f"{a.date} {a.time} | {MARKET_LABELS.get(a.market, a.market)} {a.code} {a.name} | "
                         f"{_one_line(a.subject)}")
        if paged.more("則"):
            lines.append("\n" + paged.more("則"))
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_company_major_news(code: str = "", date: TradingDate = "", year: str = "", market: Market = "",
                               limit: Limit = 50, offset: Offset = 0) -> str:
        """查詢重大訊息（公開資訊觀測站），上市、上櫃、興櫃、公發公司皆可。
        指定 code：列出該公司某年度的重大訊息（由新到舊，每則附符合條款、事實發生日與說明全文）。
        不指定 code：列出某一天全市場的重大訊息主旨（預設最近一個有公告的日子）。

        回傳：發言日期與時間、公司、主旨；指定 code 時另含符合條款、事實發生日、發言人與說明全文

        Args:
            code: 股票代號（選填），例如 "2330"
            date: 發言日期 西元 YYYYMMDD（選填）。搭配 code 時只看該日；不搭配 code 時查該日全市場
            year: 年度，西元或民國（選填，僅搭配 code；預設今年）
            market: 市場別篩選（選填，僅全市場模式）：sii 上市、otc 上櫃、rotc 興櫃、pub 公發
            limit: 回傳則數上限（預設 50；指定 code 時每頁最多 10 則，因每則全文需另外查詢）
            offset: 跳過前 N 則（預設 0，搭配 limit 分頁）
        """
        if code.strip():
            return _company(code.strip(), date.strip(), year.strip(), limit, offset)
        return _market(date.strip(), market, limit, offset)
