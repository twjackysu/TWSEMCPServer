"""Treasury-stock buybacks (庫藏股買回) and endorsements/guarantees & fund lending
(背書保證與資金貸放餘額) from the legacy MOPS pages ajax_t35sc09 / ajax_t05st11.

Neither has an OpenAPI counterpart among our tools. Buybacks come from the t35sc09 gateway
(``sources.mops.t35sc09``); the lending page's tables, which have no ids, are printed as they are
(parse_html_tables), so no column is read by position.
"""

from datetime import timedelta
from typing import Literal, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.mops.t35sc09 import Buyback, treasury_buybacks
from utils import TWSEAPIClient, format_list_response, printed, DEFAULT_DISPLAY_LIMIT
from toolkit import Limit, Offset, TradingDate, handle_api_errors
from utils.date_helper import taipei_today
from utils.mops import mops_legacy_post, parse_html_tables, to_roc_year

Market = Literal["sii", "otc", "rotc", "pub"]  # MARKETS
MARKETS = {"sii": "上市", "otc": "上櫃", "rotc": "興櫃", "pub": "公開發行"}
BUYBACK_PURPOSES = {"1": "轉讓股份予員工", "2": "股權轉換", "3": "維護公司信用及股東權益"}
DEFAULT_BUYBACK_DAYS = 90
NO_DATA_TEXT = "查無資料"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_treasury_stock_buybacks(start_date: TradingDate = "", end_date: TradingDate = "", market: Market = "sii",
                                    code: str = "", limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢公司買回自己公司股份（庫藏股）彙總：董事會決議日、買回目的、預定股數、價格區間、
        買回期間與執行結果（已買回股數、平均價格、執行率）。預設近 90 天內決議的案件。

        回傳：每筆庫藏股案件的公司、決議日、目的、金額上限、預定買回股數、價格區間、買回期間、
        是否執行完畢、已買回股數與金額、平均每股價格、佔預定股數與已發行股數比例

        Args:
            start_date: 董事會決議日期起 西元 YYYYMMDD（選填，預設 90 天前）
            end_date: 董事會決議日期迄 西元 YYYYMMDD（選填，預設今天）
            market: sii＝上市（預設）、otc＝上櫃、rotc＝興櫃、pub＝公開發行
            code: 股票代號（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        today = taipei_today()
        start = start_date.strip() or f"{today - timedelta(days=DEFAULT_BUYBACK_DAYS):%Y%m%d}"
        end = end_date.strip() or f"{today:%Y%m%d}"

        rows = treasury_buybacks(_client, market, start, end) or []
        if code.strip():
            rows = [b for b in rows if b.code == code.strip()]

        def fmt(b: Buyback) -> str:
            purpose = BUYBACK_PURPOSES.get(b.purpose, b.purpose)
            # 「是否執行完畢」Y 代表本次買回程序已結束（可能未買足，原因在最後一欄），照原文呈現
            done = f"是否執行完畢:{b.completed or '-'}"
            result = ""
            if b.bought_shares is not None:
                result = (f" | 已買回:{printed(b.bought_shares)}股（佔預定 {printed(b.pct_of_planned, '')}%，"
                          f"佔已發行 {printed(b.pct_of_issued, '')}%） 金額:{printed(b.bought_amount, '')} "
                          f"均價:{printed(b.average_price, '')}"
                          + (f" | 未完畢原因:{b.unfinished_reason}" if b.unfinished_reason else ""))
            return (
                f"{b.code} {b.name} | 決議:{b.resolution_date} | 目的:{purpose} | 上限:{printed(b.amount_cap, '')}元 | "
                f"預定:{printed(b.planned_shares, '')}股 @{printed(b.price_low, '')}～{printed(b.price_high, '')} | "
                f"期間:{b.period_start}～{b.period_end} | {done}{result}\n"
            )

        return format_list_response(
            rows, f" {start}～{end} {MARKETS[market]}公司庫藏股買回", fmt, limit, offset
        )

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_lending_and_guarantees(code: str, year: str = "", month: str = "") -> str:
        """查詢公司背書保證與資金貸與餘額（公開資訊觀測站）：預設最新月份，也可查過去月份。
        用於評估公司（含子公司）對外資金貸放與背書保證的風險曝險，含對大陸地區背書保證。

        回傳：本公司及子公司的資金貸放餘額（本月、上月、最高限額）、背書保證（本月增減、累計餘額、
        最高額度）、母子公司間背書保證、對大陸地區背書保證（單位：新台幣仟元）

        Args:
            code: 股票代號，例如 "2317"
            year: 年度，西元或民國（選填；與 month 同時留空＝最新月份）
            month: 月份 1～12（選填）
        """
        if bool(year.strip()) != bool(month.strip()):
            raise ToolError("請同時指定 year 與 month，或兩者都留空查詢最新月份")
        if year.strip():
            m = int(month)
            if not 1 <= m <= 12:
                raise ToolError("month 必須是 1～12")
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
                lines.append(" ".join(c for r in t for c in r if c))
            else:
                lines.append("")
                for r in t:
                    lines.append(" | ".join(c for c in r if c))
        return "【背書保證與資金貸放餘額】\n" + "\n".join(line for line in lines if line is not None).strip()
