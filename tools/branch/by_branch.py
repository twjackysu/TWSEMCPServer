"""分點視角的查詢：某分點一段期間買賣超了哪些股票、逐日進出紀錄。

Both tools read ``branch_stock_daily``, which carries ``idx_bsd_branch_date`` —
``(branch_code, trade_date) INCLUDE (stock_id, buy_vol, sell_vol)``. The price-level
table has no branch-first index, so a branch-centric question must never be answered
from it.

Average prices over a period are volume weighted (Σamt ÷ Σvol), computed in SQL from
the stored amount columns. Averaging each day's average price instead would weight a
one-lot day the same as a five-hundred-lot day.
"""

from typing import Optional

from fastmcp import FastMCP

from utils import (
    MSG_BRANCH_DB_NOT_CONFIGURED,
    MSG_BRANCH_STOCK_NOT_COVERED,
    TWSEAPIClient,
    handle_api_errors,
)
from utils.branch_format import (
    format_avg_price,
    format_date,
    format_lots,
    format_lots_signed,
    sum_field,
)
from utils.branch_query import (
    resolve_branch,
    resolve_broker,
    resolve_date_range,
    stock_is_covered,
)
from utils.neon_db import get_branch_db

SIDES = ("both", "buy", "sell", "net")

RANKING_BY_BRANCH_SQL = """
SELECT d.stock_id,
       s.stock_name,
       sum(d.buy_vol)               AS buy_vol,
       sum(d.sell_vol)              AS sell_vol,
       sum(d.buy_amt)               AS buy_amt,
       sum(d.sell_amt)              AS sell_amt,
       sum(d.net_vol)               AS net_vol,
       count(DISTINCT d.trade_date) AS days
FROM branch_stock_daily d
LEFT JOIN stocks s ON s.stock_id = d.stock_id
WHERE d.branch_code = %s AND d.trade_date BETWEEN %s AND %s
GROUP BY d.stock_id, s.stock_name
"""

RANKING_BY_BROKER_SQL = """
SELECT d.stock_id,
       s.stock_name,
       sum(d.buy_vol)               AS buy_vol,
       sum(d.sell_vol)              AS sell_vol,
       sum(d.buy_amt)               AS buy_amt,
       sum(d.sell_amt)              AS sell_amt,
       sum(d.net_vol)               AS net_vol,
       count(DISTINCT d.trade_date) AS days,
       count(DISTINCT d.branch_code) AS branch_count
FROM branch_stock_daily d
JOIN broker_branches b ON b.branch_code = d.branch_code
LEFT JOIN stocks s ON s.stock_id = d.stock_id
WHERE b.broker_code = %s AND d.trade_date BETWEEN %s AND %s
GROUP BY d.stock_id, s.stock_name
"""

HISTORY_SQL = """
SELECT d.trade_date,
       d.stock_id,
       s.stock_name,
       d.buy_vol,
       d.sell_vol,
       d.buy_amt,
       d.sell_amt,
       d.net_vol
FROM branch_stock_daily d
LEFT JOIN stocks s ON s.stock_id = d.stock_id
WHERE d.branch_code = %s AND d.trade_date BETWEEN %s AND %s
ORDER BY d.trade_date DESC, abs(d.net_vol) DESC
"""

HISTORY_ONE_STOCK_SQL = """
SELECT d.trade_date,
       d.stock_id,
       s.stock_name,
       d.buy_vol,
       d.sell_vol,
       d.buy_amt,
       d.sell_amt,
       d.net_vol
FROM branch_stock_daily d
LEFT JOIN stocks s ON s.stock_id = d.stock_id
WHERE d.branch_code = %s AND d.stock_id = %s AND d.trade_date BETWEEN %s AND %s
ORDER BY d.trade_date DESC
"""


def _net(row: dict) -> float:
    value = row.get("net_vol")
    return float(value) if value is not None else 0.0


def _stock_label(row: dict) -> str:
    name = row.get("stock_name")
    return f"{row['stock_id']} {name}" if name else str(row["stock_id"])


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the per-branch tools."""

    @mcp.tool
    @handle_api_errors()
    def get_branch_stock_ranking(
        branch: str,
        start_date: str = "",
        end_date: str = "",
        side: str = "both",
        group_by: str = "branch",
        limit: int = 30,
        offset: int = 0,
    ) -> str:
        """查詢某一分點（或券商總公司）在一段期間內買賣超了哪些股票，含期間加權均價。

        Args:
            branch: 分點代號（區分大小寫）或名稱關鍵字，例如 "9600" 或 "富邦"；
                group_by="broker" 時也可直接給券商名稱
            start_date: 起始日 YYYY-MM-DD 或 YYYYMMDD（選填，留空代表最近 20 個交易日）
            end_date: 結束日（選填，留空代表資料最新日）
            side: "both"（預設，買超前 N 與賣超前 N）、"buy"、"sell"、
                "net"（依買賣超絕對值排行）
            group_by: "branch"（預設，單一分點）或 "broker"（該券商所有分點合計，
                需先回填 broker_code）
            limit: 每個方向回傳的股票數上限（預設 30）
            offset: 跳過前 N 筆（預設 0）；僅在 side 為 "buy"/"sell"/"net" 時生效

        Returns:
            依買賣超排序的股票清單，含期間買／賣張數、買賣超、期間加權買賣均價與有交易天數
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        side = (side or "both").strip().lower()
        group_by = (group_by or "branch").strip().lower()
        if side not in SIDES:
            return f"side 只接受 {', '.join(SIDES)}，收到 {side!r}"
        if group_by not in ("branch", "broker"):
            return f"group_by 只接受 \"branch\" 或 \"broker\"，收到 {group_by!r}"

        if group_by == "broker":
            target = resolve_broker(db, branch)
            if isinstance(target, str):
                return target
            sql, key = RANKING_BY_BROKER_SQL, target.code
            label = target.label
        else:
            target = resolve_branch(db, branch)
            if isinstance(target, str):
                return target
            sql, key = RANKING_BY_BRANCH_SQL, target.code
            label = target.label

        window = resolve_date_range(db, start_date, end_date, default_days=20)
        if isinstance(window, str):
            return window
        start, end = window

        rows = db.query(sql, (key, start, end), max_rows=5000)
        if not rows:
            return (
                f"{label} 在 {format_date(start)} ~ {format_date(end)} 期間沒有進出紀錄。"
                "（分點資料庫只收錄已匯入的股票，可用 get_branch_data_coverage 查看）"
            )

        total_buy = sum_field(rows, "buy_vol")
        total_sell = sum_field(rows, "sell_vol")
        total_buy_amt = sum_field(rows, "buy_amt")
        total_sell_amt = sum_field(rows, "sell_amt")

        lines = [
            f"{label} {format_date(start)} ~ {format_date(end)} 期間進出 "
            f"{len(rows):,} 檔股票",
            f"期間合計：買 {format_lots(total_buy)} 張 / 賣 {format_lots(total_sell)} 張，"
            f"買賣超 {format_lots_signed(total_buy - total_sell)} 張，"
            f"買進均價 {format_avg_price(total_buy_amt, total_buy)}"
            f" / 賣出均價 {format_avg_price(total_sell_amt, total_sell)}",
        ]

        def section(title: str, ordered: list) -> None:
            page = ordered[offset : offset + limit] if side != "both" else ordered[:limit]
            if not page:
                return
            lines.append("")
            lines.append(f"{title}：")
            for row in page:
                branches = (
                    f"，{int(row['branch_count']):,} 個分點"
                    if group_by == "broker" and row.get("branch_count")
                    else ""
                )
                lines.append(
                    f"- {_stock_label(row)} "
                    f"買賣超 {format_lots_signed(row.get('net_vol'))} 張"
                    f"（買 {format_lots(row.get('buy_vol'))} / 賣 {format_lots(row.get('sell_vol'))} 張）"
                    f"買均價 {format_avg_price(row.get('buy_amt'), row.get('buy_vol'))}"
                    f" / 賣均價 {format_avg_price(row.get('sell_amt'), row.get('sell_vol'))}"
                    f"，有交易 {int(row.get('days') or 0):,} 天{branches}"
                )
            shown = offset + len(page) if side != "both" else len(page)
            if len(ordered) > shown:
                lines.append(
                    f"... 還有 {len(ordered) - shown:,} 檔"
                    + (f"，使用 offset={shown} 查看更多" if side != "both" else "")
                )

        if side == "both":
            buyers = [r for r in sorted(rows, key=_net, reverse=True) if _net(r) > 0]
            sellers = [r for r in sorted(rows, key=_net) if _net(r) < 0]
            section(f"買超前 {min(limit, len(buyers)):,} 檔", buyers)
            section(f"賣超前 {min(limit, len(sellers)):,} 檔", sellers)
        elif side == "buy":
            section("買超排行", sorted(rows, key=_net, reverse=True))
        elif side == "sell":
            section("賣超排行", sorted(rows, key=_net))
        else:
            section("買賣超絕對值排行", sorted(rows, key=lambda r: abs(_net(r)), reverse=True))

        lines.append(
            "\n說明：數量單位為「張」（1 張 = 1000 股）；均價為期間加權均價"
            "（成交金額合計 ÷ 成交股數合計），非每日均價的平均。"
        )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_branch_daily_history(
        branch: str,
        stock_id: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 60,
        offset: int = 0,
    ) -> str:
        """查詢某一分點的逐日進出紀錄，可選擇只看某一檔股票。

        Args:
            branch: 分點代號（區分大小寫）或名稱關鍵字，例如 "9600" 或 "富邦"
            stock_id: 股票代號（選填）。留空則列出該分點每天在各股的進出
            start_date: 起始日 YYYY-MM-DD 或 YYYYMMDD（選填，留空代表最近 20 個交易日）
            end_date: 結束日（選填，留空代表資料最新日）
            limit: 回傳筆數上限（預設 60）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            由新到舊排列的逐日紀錄，含買／賣張數、買賣超與當日買賣均價
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        resolved = resolve_branch(db, branch)
        if isinstance(resolved, str):
            return resolved

        stock_id = (stock_id or "").strip()
        if stock_id and not stock_is_covered(db, stock_id):
            return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

        window = resolve_date_range(db, start_date, end_date, default_days=20)
        if isinstance(window, str):
            return window
        start, end = window

        if stock_id:
            rows = db.query(
                HISTORY_ONE_STOCK_SQL, (resolved.code, stock_id, start, end), max_rows=5000
            )
        else:
            rows = db.query(HISTORY_SQL, (resolved.code, start, end), max_rows=5000)

        scope = f" × {stock_id}" if stock_id else ""
        if not rows:
            return (
                f"{resolved.label}{scope} 在 {format_date(start)} ~ {format_date(end)} "
                "期間沒有進出紀錄。"
            )

        total = len(rows)
        if offset >= total:
            return f"offset={offset} 已超出範圍，{resolved.label}{scope} 期間共 {total:,} 筆。"

        page = rows[offset : offset + limit]
        end_index = min(offset + limit, total)
        header = (
            f"{resolved.label}{scope} 逐日進出 {format_date(start)} ~ {format_date(end)}，"
            f"共 {total:,} 筆"
        )
        if total > limit or offset > 0:
            header += f"（顯示第 {offset + 1}–{end_index} 筆）"
        lines = [header, ""]
        for row in page:
            stock = "" if stock_id else f" {_stock_label(row)}"
            lines.append(
                f"- {format_date(row['trade_date'])}{stock}  "
                f"買 {format_lots(row.get('buy_vol'))} / 賣 {format_lots(row.get('sell_vol'))} 張，"
                f"買賣超 {format_lots_signed(row.get('net_vol'))} 張，"
                f"買均價 {format_avg_price(row.get('buy_amt'), row.get('buy_vol'))}"
                f" / 賣均價 {format_avg_price(row.get('sell_amt'), row.get('sell_vol'))}"
            )
        if total > end_index:
            lines.append(f"\n... 還有 {total - end_index:,} 筆，使用 offset={end_index} 查看更多")
        lines.append("\n說明：數量單位為「張」（1 張 = 1000 股）。")
        return "\n".join(lines)
