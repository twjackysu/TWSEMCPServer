"""Treasury-stock buybacks (庫藏股買回) and endorsements/guarantees & fund lending
(背書保證與資金貸放餘額) from the legacy MOPS pages ajax_t35sc09 / ajax_t05st11.

Neither has an OpenAPI counterpart among our tools. Both pages return HTML tables without
ids, read with parse_html_tables.
"""

from datetime import timedelta
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_list_response, DEFAULT_DISPLAY_LIMIT
from utils.date_helper import taipei_today
from utils.mops import mops_legacy_post, parse_html_tables, to_roc_year

MARKETS = {"sii": "上市", "otc": "上櫃", "rotc": "興櫃", "pub": "公開發行"}
BUYBACK_PURPOSES = {"1": "轉讓股份予員工", "2": "股權轉換", "3": "維護公司信用及股東權益"}
# Buyback data rows are 20 cells wide (the two-row header has 18 + 4 sub-headers).
BUYBACK_ROW_WIDTH = 20
DEFAULT_BUYBACK_DAYS = 90
NO_DATA_TEXT = "查無資料"


def _roc_compact(date: str) -> Optional[str]:
    """YYYYMMDD → ROC "YYYMMDD" as t35sc09 takes it, or None."""
    if len(date) != 8 or not date.isdigit():
        return None
    return f"{int(date[:4]) - 1911:03d}{date[4:]}"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_treasury_stock_buybacks(start_date: str = "", end_date: str = "", market: str = "sii",
                                    code: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢公司買回自己公司股份（庫藏股）彙總：董事會決議日、買回目的、預定股數、價格區間、
        買回期間與執行結果（已買回股數、平均價格、執行率）。預設近 90 天內決議的案件。

        Args:
            start_date: 董事會決議日期起 YYYYMMDD（選填，預設 90 天前）
            end_date: 董事會決議日期迄 YYYYMMDD（選填，預設今天）
            market: sii＝上市（預設）、otc＝上櫃、rotc＝興櫃、pub＝公開發行
            code: 股票代號（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每筆庫藏股案件的公司、決議日、目的、金額上限、預定買回股數、價格區間、買回期間、
            是否執行完畢、已買回股數與金額、平均每股價格、佔預定股數與已發行股數比例
        """
        market = market.strip().lower()
        if market not in MARKETS:
            return f"market 只能是 {', '.join(MARKETS)}"
        today = taipei_today()
        start = start_date.strip() or f"{today - timedelta(days=DEFAULT_BUYBACK_DAYS):%Y%m%d}"
        end = end_date.strip() or f"{today:%Y%m%d}"
        d1, d2 = _roc_compact(start), _roc_compact(end)
        if not d1 or not d2:
            return "日期格式錯誤，請使用 YYYYMMDD，例如 \"20260101\""

        html = mops_legacy_post(_client, "ajax_t35sc09", {"TYPEK": market, "d1": d1, "d2": d2, "RD": "1"})
        rows = [r for table in parse_html_tables(html) for r in table
                if len(r) == BUYBACK_ROW_WIDTH and r[0].strip().isdigit()]
        if not rows and NO_DATA_TEXT not in html and "買回" not in html:
            raise ValueError("公開資訊觀測站回應非預期頁面（可能暫時限制存取或頁面改版），請稍後再試")
        if code.strip():
            rows = [r for r in rows if r[1].strip() == code.strip()]

        def fmt(r):
            # r: 序號,代號,名稱,董事會決議日期,買回目的,金額上限,預定買回股數,價格最低,價格最高,期間起,期間迄,
            #    是否執行完畢,達一定標準資料,已買回股數,已註銷或轉讓股數,佔預定比例(%),已買回總金額,
            #    平均每股價格,佔已發行股份比例(%),未執行完畢原因
            purpose = BUYBACK_PURPOSES.get(r[4].strip(), r[4])
            # 「是否執行完畢」Y 代表本次買回程序已結束（可能未買足，原因在最後一欄），照原文呈現
            done = f"是否執行完畢:{r[11].strip() or '-'}"
            result = ""
            if r[13].strip():
                result = (f" | 已買回:{r[13]}股（佔預定 {r[15]}%，佔已發行 {r[18]}%）"
                          f" 金額:{r[16]} 均價:{r[17]}" + (f" | 未完畢原因:{r[19]}" if r[19].strip() else ""))
            return (
                f"{r[1]} {r[2]} | 決議:{r[3]} | 目的:{purpose} | 上限:{r[5]}元 | 預定:{r[6]}股 "
                f"@{r[7]}～{r[8]} | 期間:{r[9]}～{r[10]} | {done}{result}\n"
            )

        return format_list_response(
            rows, f" {start}～{end} {MARKETS[market]}公司庫藏股買回", fmt, limit, offset
        )

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_lending_and_guarantees(code: str, year: str = "", month: str = "") -> str:
        """查詢公司背書保證與資金貸與餘額（公開資訊觀測站）：預設最新月份，也可查過去月份。
        用於評估公司（含子公司）對外資金貸放與背書保證的風險曝險，含對大陸地區背書保證。

        Args:
            code: 股票代號，例如 "2317"
            year: 年度，西元或民國（選填；與 month 同時留空＝最新月份）
            month: 月份 1～12（選填）

        Returns:
            本公司及子公司的資金貸放餘額（本月、上月、最高限額）、背書保證（本月增減、累計餘額、
            最高額度）、母子公司間背書保證、對大陸地區背書保證（單位：新台幣仟元）
        """
        if bool(year.strip()) != bool(month.strip()):
            return "請同時指定 year 與 month，或兩者都留空查詢最新月份"
        if year.strip():
            m = int(month)
            if not 1 <= m <= 12:
                return "month 必須是 1～12"
            form = {"co_id": code.strip(), "isnew": "false", "year": str(to_roc_year(year)), "month": f"{m:02d}"}
        else:
            form = {"co_id": code.strip(), "isnew": "true", "year": "", "month": ""}

        html = mops_legacy_post(_client, "ajax_t05st11", form)
        tables = [t for t in parse_html_tables(html) if t]
        # 第一張有內容的表是「本資料由 (市場) 公司 公司提供」，其後依序為月份/單位、資金貸放、
        # 背書保證、母子公司間、對大陸地區
        data_tables = [t for t in tables if any(len(r) > 1 for r in t)]
        if not data_tables:
            if NO_DATA_TEXT in html:
                return f"查無 {code} 的背書保證與資金貸放資料（該月份可能尚未申報）"
            raise ValueError("公開資訊觀測站回應非預期頁面（可能暫時限制存取或頁面改版），請稍後再試")

        lines = []
        for t in tables:
            if all(len(r) <= 1 for r in t):
                lines.append(" ".join(r[0] for r in t if r and r[0]))
            else:
                lines.append("")
                for r in t:
                    lines.append(" | ".join(c for c in r if c))
        return "【背書保證與資金貸放餘額】\n" + "\n".join(line for line in lines if line is not None).strip()
