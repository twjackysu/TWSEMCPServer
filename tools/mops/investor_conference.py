"""Investor conferences (法人說明會) from MOPS legacy page ajax_t100sb02_1.

The new MOPS front end forwards this page to the legacy mopsov site (action type "twse"),
which returns an HTML table rather than JSON; ``sources.mops.investor_conference`` reads it.
"""

from typing import Literal, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.mops.investor_conference import investor_conferences
from utils import TWSEAPIClient, truncate, Page
from toolkit import Limit, Offset, handle_api_errors
from utils.mops import to_roc_year

Market = Literal["sii", "otc", "rotc", "pub"]  # MARKETS
MARKETS = {"sii": "上市", "otc": "上櫃", "rotc": "興櫃", "pub": "公開發行"}


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS investor conference tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_investor_conferences(year: str, month: str = "", code: str = "", market: Market = "sii",
                                 limit: Limit = 30, offset: Offset = 0) -> str:
        """查詢法人說明會（法說會）公告：日期、地點、擇要訊息、簡報檔案（公開資訊觀測站）。
        可查某公司整年的法說會，或某月份全市場的法說會行事曆。

        回傳：每場法說會的公司、日期、時間、地點、擇要訊息（內容摘要）、中英文簡報檔名、公司網站連結

        Args:
            year: 公告年度，西元（"2026"）或民國（"115"）皆可
            month: 月份 1～12（選填）。未指定 code 時建議填寫，否則會回傳整年全市場資料
            code: 股票代號（選填），例如 "2330"
            market: 市場別：sii＝上市（預設）、otc＝上櫃、rotc＝興櫃、pub＝公開發行
            limit: 回傳筆數上限（預設 30）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        roc_year = to_roc_year(year)
        m = None
        if month.strip():
            m = int(month)
            if not 1 <= m <= 12:
                raise ToolError("month 必須是 1～12")

        # 來源依公司代號排序；改依召開日期（民國 YYY/MM/DD，字串排序即時間順序）方便當行事曆看
        rows = sorted(investor_conferences(_client, market, roc_year, m, code.strip()), key=lambda c: c.date)
        scope = f"{MARKETS[market]} 民國{roc_year}年" + (f"{m:02d}月" if m else "") + (f" {code}" if code else "")
        if not rows:
            return f"查無 {scope} 的法人說明會資料"

        paged = Page(limit, offset).take(rows)
        if paged.past_end:
            return paged.out_of_range(f"{scope} 的法說會資料")
        header = f"【法人說明會 {scope}】（共 {paged.total} 筆"
        if paged.span():
            header += f"，{paged.span()}"
        header += "）\n"

        lines = [header]
        for c in paged.rows:
            lines.append(
                f"{c.date} {c.time} | {c.code} {c.name} | 地點:{truncate(c.place, 60)}\n"
                f"  摘要:{truncate(c.summary, 200)}\n"
                f"  簡報:{c.file_zh or '-'} / {c.file_en or '-'} | 網站:{c.website or '-'}"
            )
        if paged.more():
            lines.append("\n" + paged.more())
        return "\n".join(lines)
