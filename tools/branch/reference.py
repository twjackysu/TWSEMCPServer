"""分點資料庫的輔助查詢：資料覆蓋範圍、分點代號查詢。

``get_branch_data_coverage`` exists because this database only holds what the user's
own import pipeline has loaded. Without it a caller cannot tell "this branch did not
trade that stock" from "that stock was never imported", and would read an empty
result as a market fact.
"""

from typing import Optional

from fastmcp import FastMCP

from utils import (
    MSG_BRANCH_DB_NOT_CONFIGURED,
    MSG_BRANCH_STOCK_NOT_COVERED,
    TWSEAPIClient,
    handle_api_errors,
)
from utils.branch_format import format_date, format_lots
from utils.neon_db import get_branch_db

COVERAGE_SUMMARY_SQL = """
SELECT (SELECT count(*) FROM broker_branches)                      AS branches,
       (SELECT count(broker_code) FROM broker_branches)            AS branches_mapped,
       (SELECT count(*) FROM brokers)                              AS brokers,
       (SELECT count(*) FROM stocks)                               AS stocks,
       (SELECT min(trade_date) FROM branch_stock_daily)            AS d_min,
       (SELECT max(trade_date) FROM branch_stock_daily)            AS d_max,
       (SELECT count(DISTINCT trade_date) FROM branch_stock_daily) AS days
"""

COVERAGE_BY_STOCK_SQL = """
SELECT d.stock_id,
       s.stock_name,
       s.market,
       min(d.trade_date)            AS d_min,
       max(d.trade_date)            AS d_max,
       count(DISTINCT d.trade_date) AS days,
       count(*)                     AS row_count,
       sum(d.buy_vol)               AS buy_vol,
       sum(d.sell_vol)              AS sell_vol
FROM branch_stock_daily d
LEFT JOIN stocks s ON s.stock_id = d.stock_id
GROUP BY d.stock_id, s.stock_name, s.market
ORDER BY d.stock_id
"""

COVERAGE_DATES_SQL = """
SELECT d.trade_date,
       count(*)           AS branches,
       sum(d.buy_vol)     AS buy_vol,
       sum(d.sell_vol)    AS sell_vol,
       l.row_count        AS import_rows,
       l.total_vol        AS import_vol
FROM branch_stock_daily d
LEFT JOIN import_log l
       ON l.trade_date = d.trade_date AND l.stock_id = d.stock_id
WHERE d.stock_id = %s
GROUP BY d.trade_date, l.row_count, l.total_vol
ORDER BY d.trade_date DESC
"""

SEARCH_BRANCH_SQL = """
SELECT b.branch_code,
       b.branch_name,
       b.broker_code,
       k.broker_name,
       b.first_seen,
       b.last_seen
FROM broker_branches b
LEFT JOIN brokers k ON k.broker_code = b.broker_code
WHERE b.branch_name ILIKE %s OR b.branch_code ILIKE %s
ORDER BY b.branch_code
"""


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the branch-database reference tools."""

    @mcp.tool
    @handle_api_errors()
    def get_branch_data_coverage(stock_id: str = "") -> str:
        """查詢分點進出資料庫目前收錄了哪些股票與日期範圍（建議先查這支再查其他分點工具）。

        這個資料庫的內容取決於使用者自己的匯入流程，不是整個市場都有。查詢未收錄的
        股票時其他工具會明確回「未收錄」而不是「無資料」，避免被誤讀成「沒人買賣」。

        Args:
            stock_id: 股票代號（選填）。留空列出所有已收錄股票；填入則列出該股每個
                有資料的交易日，並與 import_log 的匯入筆數對照

        Returns:
            資料涵蓋的日期範圍、股票清單、分點與券商主檔狀態；成交量以「張」顯示
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        if stock_id:
            stock_id = stock_id.strip()
            rows = db.query(COVERAGE_DATES_SQL, (stock_id,), max_rows=2000)
            if not rows:
                return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

            lines = [
                f"股票 {stock_id} 在分點資料庫的覆蓋情形："
                f"{format_date(rows[-1]['trade_date'])} ~ {format_date(rows[0]['trade_date'])}，"
                f"共 {len(rows)} 個交易日\n"
            ]
            for row in rows:
                buy, sell = row.get("buy_vol"), row.get("sell_vol")
                # The import流程 validates Σbuy = Σsell; flag a day where it does not
                # hold, because that means the rollup for that day is not trustworthy.
                warn = "" if buy == sell else "  ⚠ 買賣量不相等"
                imported = (
                    f"，明細 {int(row['import_rows']):,} 筆"
                    if row.get("import_rows") is not None
                    else "，無 import_log 紀錄"
                )
                lines.append(
                    f"- {format_date(row['trade_date'])} "
                    f"{int(row['branches']):,} 個分點，"
                    f"買 {format_lots(buy)} 張 / 賣 {format_lots(sell)} 張"
                    f"{imported}{warn}"
                )
            return "\n".join(lines)

        summary = db.query_one(COVERAGE_SUMMARY_SQL) or {}
        stocks = db.query(COVERAGE_BY_STOCK_SQL, max_rows=5000)

        if not stocks:
            return (
                "分點資料庫目前沒有任何交易資料。\n"
                f"分點主檔 {int(summary.get('branches') or 0):,} 個、"
                f"券商總公司 {int(summary.get('brokers') or 0):,} 家、"
                f"股票主檔 {int(summary.get('stocks') or 0):,} 檔。"
            )

        mapped = int(summary.get("branches_mapped") or 0)
        branches = int(summary.get("branches") or 0)
        lines = [
            "分點進出資料庫覆蓋範圍",
            f"日期範圍：{format_date(summary.get('d_min'))} ~ {format_date(summary.get('d_max'))}"
            f"（{int(summary.get('days') or 0):,} 個交易日）",
            f"分點主檔 {branches:,} 個（已對應券商總公司 {mapped:,} 個）、"
            f"券商總公司 {int(summary.get('brokers') or 0):,} 家、"
            f"股票主檔 {int(summary.get('stocks') or 0):,} 檔",
            "",
            f"共收錄 {len(stocks):,} 檔股票：",
        ]
        for row in stocks:
            name = row.get("stock_name") or "（股票主檔無名稱）"
            market = f" {row['market']}" if row.get("market") else ""
            lines.append(
                f"- {row['stock_id']} {name}{market} "
                f"{format_date(row['d_min'])} ~ {format_date(row['d_max'])}，"
                f"{int(row['days']):,} 個交易日，{int(row['row_count']):,} 筆，"
                f"買 {format_lots(row.get('buy_vol'))} 張 / 賣 {format_lots(row.get('sell_vol'))} 張"
            )

        notes = ["", "說明：成交量單位為「張」（資料庫以股儲存，1 張 = 1000 股）。"]
        if mapped == 0:
            notes.append(
                "broker_code 尚未回填，因此無法依券商總公司彙總（group_by=\"broker\"）；"
                "可執行 backfill_branch_reference_data(dry_run=True) 先試算。"
            )
        if int(summary.get("stocks") or 0) == 0:
            notes.append(
                "stocks 主檔為空，因此清單只有代號沒有股票名稱；"
                "同一支回填工具可一併補上（target=\"stocks\"）。"
            )
        return "\n".join(lines + notes)

    @mcp.tool
    @handle_api_errors()
    def search_broker_branch(keyword: str, limit: int = 50, offset: int = 0) -> str:
        """以名稱關鍵字或代號前綴查詢分點（券商分公司）代號。

        分點代號區分大小寫：'9A9d' 是永豐古亭、'9A9D' 是永豐忠孝，兩個不同分點。
        這裡的名稱與代號比對不分大小寫方便尋找，但把代號拿去其他工具查詢時必須照
        本工具回傳的大小寫原樣使用。

        Args:
            keyword: 分點名稱關鍵字（例如 "富邦"、"永豐古亭"）或代號前綴（例如 "9A9"）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            分點代號、名稱、所屬券商總公司（若已回填）、首次與最後出現的交易日
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        keyword = (keyword or "").strip()
        if not keyword:
            return "請提供分點名稱關鍵字或代號前綴，例如 keyword=\"富邦\" 或 keyword=\"9A9\"。"

        pattern = _escape_like(keyword)
        rows = db.query(
            SEARCH_BRANCH_SQL,
            (f"%{pattern}%", f"{pattern}%"),
            max_rows=2000,
        )
        if not rows:
            return f"查無名稱或代號符合「{keyword}」的分點。"

        total = len(rows)
        if offset >= total:
            return f"offset={offset} 已超出範圍，符合「{keyword}」的分點共 {total} 個。"

        page = rows[offset : offset + limit]
        end = min(offset + limit, total)
        header = f"符合「{keyword}」的分點共 {total} 個"
        if total > limit or offset > 0:
            header += f"（顯示第 {offset + 1}–{end} 個）"
        lines = [header + "：", ""]
        for row in page:
            broker = (
                f"，所屬券商 {row['broker_name']} ({row['broker_code']})"
                if row.get("broker_code")
                else "，尚未對應券商總公司"
            )
            lines.append(
                f"- {row['branch_code']} {row['branch_name']}{broker}"
                f"，出現於 {format_date(row.get('first_seen'))} ~ {format_date(row.get('last_seen'))}"
            )
        remaining = total - end
        if remaining > 0:
            lines.append(f"\n... 還有 {remaining} 個，使用 offset={end} 查看更多")
        lines.append("\n注意：代號區分大小寫，請照上面的大小寫原樣使用。")
        return "\n".join(lines)
