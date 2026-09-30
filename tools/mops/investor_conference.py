"""Investor conferences (法人說明會) from MOPS legacy page ajax_t100sb02_1.

The new MOPS front end forwards this page to the legacy mopsov site (action type "twse"),
which returns an HTML table rather than JSON.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, truncate, MSG_OFFSET_OUT_OF_RANGE
from utils.mops import mops_legacy_post, parse_html_table, to_roc_year

MARKETS = {"sii": "上市", "otc": "上櫃", "rotc": "興櫃", "pub": "公開發行"}

# Data rows of table#myTable have exactly these 12 cells, in this order:
# 公司代號, 公司名稱, 召開法人說明會日期, 召開法人說明會時間, 召開法人說明會地點,
# 法人說明會擇要訊息, 簡報中文檔案, 簡報英文檔案, 公司網站是否提供相關資訊,
# 影音連結資訊, 其他應敘明事項, 歷年法人說明會(按鈕)
ROW_WIDTH = 12

# The legacy page's own wording when a query has no rows.
NO_DATA_TEXT = "查無資料"


def parse_conference_rows(html: str) -> list:
    """Return the conference table's data rows (header rows dropped), ordered by date."""
    rows = [
        r for r in parse_html_table(html, "myTable")
        if len(r) == ROW_WIDTH and r[0] != "公司代號"
    ]
    # 來源依公司代號排序；改依召開日期（民國 YYY/MM/DD，字串排序即時間順序）方便當行事曆看
    return sorted(rows, key=lambda r: r[2])


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS investor conference tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_investor_conferences(year: str, month: str = "", code: str = "", market: str = "sii",
                                 limit: int = 30, offset: int = 0) -> str:
        """查詢法人說明會（法說會）公告：日期、地點、擇要訊息、簡報檔案（公開資訊觀測站）。
        可查某公司整年的法說會，或某月份全市場的法說會行事曆。

        Args:
            year: 公告年度，西元（"2026"）或民國（"115"）皆可
            month: 月份 1～12（選填）。未指定 code 時建議填寫，否則會回傳整年全市場資料
            code: 股票代號（選填），例如 "2330"
            market: 市場別：sii＝上市（預設）、otc＝上櫃、rotc＝興櫃、pub＝公開發行
            limit: 回傳筆數上限（預設 30）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每場法說會的公司、日期、時間、地點、擇要訊息（內容摘要）、中英文簡報檔名、公司網站連結
        """
        market = market.strip().lower()
        if market not in MARKETS:
            return f"market 只能是 {', '.join(MARKETS)}"
        roc_year = to_roc_year(year)
        month_value = ""
        if month.strip():
            m = int(month)
            if not 1 <= m <= 12:
                return "month 必須是 1～12"
            # 舊站只認補零的月份：month=9 回「查無資料」，month=09 才有資料
            month_value = f"{m:02d}"

        html = mops_legacy_post(_client, "ajax_t100sb02_1", {
            "TYPEK": market,
            "year": str(roc_year),
            "month": month_value,
            "co_id": code.strip(),
        })
        rows = parse_conference_rows(html)
        if not rows and NO_DATA_TEXT not in html:
            # 既沒有資料表也沒有「查無資料」：多半是 MOPS 的防爬封鎖頁或改版，不能回報成查無資料
            raise ValueError("公開資訊觀測站回應非預期頁面（可能暫時限制存取或頁面改版），請稍後再試")
        scope = f"{MARKETS[market]} 民國{roc_year}年" + (f"{month_value}月" if month_value else "") + (f" {code}" if code else "")
        if not rows:
            return f"查無 {scope} 的法人說明會資料"

        total = len(rows)
        page = rows[offset:offset + limit]
        if not page:
            return MSG_OFFSET_OUT_OF_RANGE.format(offset=offset, data_type=f"{scope} 的法說會資料", count=total)
        end = min(offset + limit, total)
        header = f"【法人說明會 {scope}】（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）\n"

        lines = [header]
        for r in page:
            co, name, day, time_, place, summary, file_zh, file_en, site = r[:9]
            lines.append(
                f"{day} {time_} | {co} {name} | 地點:{truncate(place, 60)}\n"
                f"  摘要:{truncate(summary, 200)}\n"
                f"  簡報:{file_zh or '-'} / {file_en or '-'} | 網站:{site or '-'}"
            )
        remaining = total - offset - limit
        if remaining > 0:
            lines.append(f"\n...還有 {remaining} 筆，使用 offset={offset + limit} 查看更多")
        return "\n".join(lines)
