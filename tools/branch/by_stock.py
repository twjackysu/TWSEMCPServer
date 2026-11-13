"""個股視角的分點進出查詢：某股某日各分點買賣超、各價位明細、某分點逐日時序。

Which table each tool reads matters for both speed and meaning:

* ``branch_stock_daily`` (the rollup) answers anything that does not need a price
  level, and is the only table indexed for branch-first access
  (``idx_bsd_branch_date``).
* ``branch_daily_trades`` (the price-level fact table) is only indexed by
  ``(stock_id, trade_date, branch_code, price)``, so it is always queried with a
  stock and a date. A single stock-day can hold several thousand rows (measured
  5,250 for 1476 on 2026-11-06: 682 branches × 68 price levels), which is why
  ``get_stock_price_detail`` aggregates by price unless one branch is named.
"""

from typing import Optional

from fastmcp import FastMCP

from utils import (
    MSG_BRANCH_DB_NOT_CONFIGURED,
    MSG_BRANCH_NO_DATA_ON_DATE,
    MSG_BRANCH_STOCK_NOT_COVERED,
    MSG_BROKER_MAPPING_MISSING,
    TWSEAPIClient,
    handle_api_errors,
)
from utils.branch_format import (
    format_avg_price,
    format_date,
    format_lots,
    format_lots_signed,
    format_price,
    parse_trade_date,
    sum_field,
    trailing_streak,
)
from utils.branch_query import (
    broker_mapping_ready,
    latest_stock_date,
    resolve_branch,
    resolve_date_range,
    stock_is_covered,
)
from utils.neon_db import get_branch_db

SIDES = ("both", "buy", "sell", "net")

BY_BRANCH_SQL = """
SELECT d.branch_code      AS code,
       b.branch_name      AS name,
       d.buy_vol,
       d.sell_vol,
       d.buy_amt,
       d.sell_amt,
       d.net_vol
FROM branch_stock_daily d
JOIN broker_branches b ON b.branch_code = d.branch_code
WHERE d.stock_id = %s AND d.trade_date = %s
"""

BY_BROKER_SQL = """
SELECT b.broker_code     AS code,
       k.broker_name     AS name,
       sum(d.buy_vol)    AS buy_vol,
       sum(d.sell_vol)   AS sell_vol,
       sum(d.buy_amt)    AS buy_amt,
       sum(d.sell_amt)   AS sell_amt,
       sum(d.net_vol)    AS net_vol,
       count(*)          AS branch_count
FROM branch_stock_daily d
JOIN broker_branches b ON b.branch_code = d.branch_code
LEFT JOIN brokers k ON k.broker_code = b.broker_code
WHERE d.stock_id = %s AND d.trade_date = %s AND b.broker_code IS NOT NULL
GROUP BY b.broker_code, k.broker_name
"""

PRICE_DETAIL_SQL = """
SELECT price,
       sum(buy_vol)              AS buy_vol,
       sum(sell_vol)             AS sell_vol,
       count(DISTINCT branch_code) AS branches
FROM branch_daily_trades
WHERE stock_id = %s AND trade_date = %s
GROUP BY price
ORDER BY price DESC
"""

PRICE_DETAIL_ONE_BRANCH_SQL = """
SELECT price,
       sum(buy_vol)              AS buy_vol,
       sum(sell_vol)             AS sell_vol,
       count(DISTINCT branch_code) AS branches
FROM branch_daily_trades
WHERE stock_id = %s AND trade_date = %s AND branch_code = %s
GROUP BY price
ORDER BY price DESC
"""

TREND_SQL = """
SELECT trade_date, buy_vol, sell_vol, buy_amt, sell_amt, net_vol
FROM branch_stock_daily
WHERE stock_id = %s AND branch_code = %s AND trade_date BETWEEN %s AND %s
ORDER BY trade_date
"""


def _row_line(row: dict, extra: str = "") -> str:
    """One ``分點/券商`` line: net first, then the two sides and their average prices."""
    name = row.get("name") or row.get("code")
    return (
        f"- {name} ({row.get('code')}){extra} "
        f"買賣超 {format_lots_signed(row.get('net_vol'))} 張"
        f"（買 {format_lots(row.get('buy_vol'))} / 賣 {format_lots(row.get('sell_vol'))} 張）"
        f"買均價 {format_avg_price(row.get('buy_amt'), row.get('buy_vol'))}"
        f" / 賣均價 {format_avg_price(row.get('sell_amt'), row.get('sell_vol'))}"
    )


def _net(row: dict) -> float:
    value = row.get("net_vol")
    return float(value) if value is not None else 0.0


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the per-stock branch tools."""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_branch_summary(
        stock_id: str,
        date: str = "",
        side: str = "both",
        group_by: str = "branch",
        limit: int = 30,
        offset: int = 0,
    ) -> str:
        """查詢某檔股票某一交易日各分點（券商分公司）的買賣超與買賣均價。

        資料來自使用者自建的分點進出資料庫。可先用 get_branch_data_coverage 確認該股
        是否已收錄、有哪些交易日。

        Args:
            stock_id: 股票代號，例如 "1476"
            date: 交易日，格式 YYYY-MM-DD 或 YYYYMMDD（選填，留空代表該股最新有資料的交易日）
            side: "both"（預設，買超前 N 與賣超前 N）、"buy"（買超排行）、
                "sell"（賣超排行）、"net"（依買賣超絕對值排行，不分方向）
            group_by: "branch"（預設，單一分點）或 "broker"（彙總為券商總公司，
                需先回填 broker_code）
            limit: 每個方向回傳的筆數上限（預設 30）
            offset: 跳過前 N 筆（預設 0）；僅在 side 為 "buy"/"sell"/"net" 時生效

        Returns:
            依買賣超排序的分點清單，含買/賣張數、買賣超張數與買賣均價（1 張 = 1000 股）
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        stock_id = (stock_id or "").strip()
        side = (side or "both").strip().lower()
        group_by = (group_by or "branch").strip().lower()
        if side not in SIDES:
            return f"side 只接受 {', '.join(SIDES)}，收到 {side!r}"
        if group_by not in ("branch", "broker"):
            return f"group_by 只接受 \"branch\" 或 \"broker\"，收到 {group_by!r}"
        if not stock_is_covered(db, stock_id):
            return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

        if date:
            try:
                trade_date = parse_trade_date(date)
            except ValueError as exc:
                return str(exc)
        else:
            trade_date = latest_stock_date(db, stock_id)
            if trade_date is None:
                return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

        if group_by == "broker":
            if not broker_mapping_ready(db):
                return MSG_BROKER_MAPPING_MISSING
            rows = db.query(BY_BROKER_SQL, (stock_id, trade_date))
            unit = "券商"
        else:
            rows = db.query(BY_BRANCH_SQL, (stock_id, trade_date))
            unit = "分點"

        if not rows:
            return MSG_BRANCH_NO_DATA_ON_DATE.format(
                stock_id=stock_id, date=format_date(trade_date)
            )

        total_buy = sum_field(rows, "buy_vol")
        total_sell = sum_field(rows, "sell_vol")
        total_buy_amt = sum_field(rows, "buy_amt")
        total_sell_amt = sum_field(rows, "sell_amt")

        lines = [
            f"{stock_id} [{format_date(trade_date)}] {unit}進出，共 {len(rows):,} 個{unit}有成交",
        ]
        # When the rows cover the whole market the two sides are the same number by
        # construction — every share bought was sold, at the same price — so the
        # totals collapse to one volume and one VWAP. Printing 買/賣 separately there
        # reads as two independent figures. They do differ when the rows are a subset
        # (group_by="broker" before every branch is mapped), so this adapts instead of
        # assuming either shape.
        if total_buy == total_sell and total_buy_amt == total_sell_amt:
            lines.append(
                f"全日成交 {format_lots(total_buy)} 張，"
                f"成交均價 {format_avg_price(total_buy_amt, total_buy)}"
            )
        else:
            lines.append(
                f"合計：買 {format_lots(total_buy)} 張 / 賣 {format_lots(total_sell)} 張，"
                f"買均價 {format_avg_price(total_buy_amt, total_buy)}"
                f" / 賣均價 {format_avg_price(total_sell_amt, total_sell)}"
            )

        def section(title: str, ordered: list) -> None:
            page = ordered[offset : offset + limit] if side != "both" else ordered[:limit]
            if not page:
                return
            lines.append("")
            lines.append(f"{title}：")
            for row in page:
                extra = (
                    f" [{int(row['branch_count']):,} 個分點]"
                    if group_by == "broker" and row.get("branch_count")
                    else ""
                )
                lines.append(_row_line(row, extra))
            shown = offset + len(page) if side != "both" else len(page)
            if len(ordered) > shown:
                lines.append(
                    f"... 還有 {len(ordered) - shown:,} 個{unit}"
                    + (f"，使用 offset={shown} 查看更多" if side != "both" else "")
                )

        if side == "both":
            buyers = [r for r in sorted(rows, key=_net, reverse=True) if _net(r) > 0]
            sellers = [r for r in sorted(rows, key=_net) if _net(r) < 0]
            section(f"買超前 {min(limit, len(buyers)):,} 個{unit}", buyers)
            section(f"賣超前 {min(limit, len(sellers)):,} 個{unit}", sellers)
        elif side == "buy":
            section("買超排行", sorted(rows, key=_net, reverse=True))
        elif side == "sell":
            section("賣超排行", sorted(rows, key=_net))
        else:
            section("買賣超絕對值排行", sorted(rows, key=lambda r: abs(_net(r)), reverse=True))

        lines.append("\n說明：數量單位為「張」（1 張 = 1000 股），均價為成交金額 ÷ 成交股數。")
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_price_detail(
        stock_id: str,
        date: str = "",
        branch: str = "",
        group_by: str = "price",
        limit: int = 60,
        offset: int = 0,
    ) -> str:
        """查詢某檔股票某一交易日的分價量表（各成交價位的成交張數）。

        這是分點資料最細的一層。不指定 branch 時回傳全市場各價位的成交量（同一價位
        的買量與賣量必然相等，故以單一成交量表示）；指定 branch 時回傳該分點在各價位
        的買進／賣出張數，可看出一個分點的成本分布。

        Args:
            stock_id: 股票代號，例如 "1476"
            date: 交易日，格式 YYYY-MM-DD 或 YYYYMMDD（選填，留空代表該股最新有資料的交易日）
            branch: 分點代號（區分大小寫）或名稱關鍵字（選填）。group_by="branch" 時必填
            group_by: "price"（預設，各價位彙總）或 "branch"（單一分點在各價位的明細，需填 branch）
            limit: 回傳價位數上限（預設 60）
            offset: 跳過前 N 個價位（預設 0，搭配 limit 分頁）

        Returns:
            由高價到低價排列的各價位成交張數；指定 branch 時為該分點的買進／賣出張數
            （1 張 = 1000 股）
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        stock_id = (stock_id or "").strip()
        group_by = (group_by or "price").strip().lower()
        if group_by not in ("price", "branch"):
            return f"group_by 只接受 \"price\" 或 \"branch\"，收到 {group_by!r}"
        if group_by == "branch" and not branch:
            # Without a branch this would be every branch × every price level —
            # several thousand rows for one stock-day.
            return (
                "group_by=\"branch\" 需要同時指定 branch（分點代號或名稱），"
                "否則單日列數可達數千列。若要看全市場各價位請用 group_by=\"price\"。"
            )
        if not stock_is_covered(db, stock_id):
            return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

        if date:
            try:
                trade_date = parse_trade_date(date)
            except ValueError as exc:
                return str(exc)
        else:
            trade_date = latest_stock_date(db, stock_id)
            if trade_date is None:
                return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

        scope = "全市場"
        if branch:
            resolved = resolve_branch(db, branch)
            if isinstance(resolved, str):
                return resolved
            scope = resolved.label
            rows = db.query(
                PRICE_DETAIL_ONE_BRANCH_SQL, (stock_id, trade_date, resolved.code)
            )
        else:
            rows = db.query(PRICE_DETAIL_SQL, (stock_id, trade_date))

        if not rows:
            if branch:
                return (
                    f"分點 {scope} 在 {format_date(trade_date)} 沒有 {stock_id} 的成交紀錄。"
                )
            return MSG_BRANCH_NO_DATA_ON_DATE.format(
                stock_id=stock_id, date=format_date(trade_date)
            )

        total = len(rows)
        if offset >= total:
            return f"offset={offset} 已超出範圍，{stock_id} 當日共 {total} 個價位。"

        total_buy = sum_field(rows, "buy_vol")
        total_sell = sum_field(rows, "sell_vol")
        page = rows[offset : offset + limit]
        end = min(offset + limit, total)

        header = f"{stock_id} [{format_date(trade_date)}] {scope} 分價量表，共 {total} 個價位"
        if total > limit or offset > 0:
            header += f"（顯示第 {offset + 1}–{end} 個）"

        # Summed over every branch, the買 and賣 columns at one price level are the same
        # number by construction — each share bought at that price was sold at it.
        # Printing them as two figures reads as if they were independent, so the
        # whole-market view reports one 成交量 and only the single-branch view splits
        # the sides (where they genuinely differ).
        if branch:
            lines = [
                header,
                f"合計：買 {format_lots(total_buy)} 張 / 賣 {format_lots(total_sell)} 張",
                "",
            ]
            for row in page:
                lines.append(
                    f"- {format_price(row['price'])}  "
                    f"買 {format_lots(row.get('buy_vol'))} 張"
                    f" / 賣 {format_lots(row.get('sell_vol'))} 張"
                )
        else:
            lines = [header, f"合計成交 {format_lots(total_buy)} 張", ""]
            for row in page:
                branches = (
                    f"（{int(row['branches']):,} 個分點）" if row.get("branches") else ""
                )
                lines.append(
                    f"- {format_price(row['price'])}  "
                    f"成交 {format_lots(row.get('buy_vol'))} 張{branches}"
                )

        if total > end:
            lines.append(f"\n... 還有 {total - end} 個價位，使用 offset={end} 查看更多")
        lines.append(
            "\n說明：數量單位為「張」（1 張 = 1000 股），價格為成交價位。"
            + (
                ""
                if branch
                else "全市場各價位的買量與賣量必然相等，故以單一「成交量」表示；"
                "要看買賣方向請指定 branch。"
            )
        )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_branch_trend(
        stock_id: str,
        branch: str,
        start_date: str = "",
        end_date: str = "",
        limit: int = 60,
    ) -> str:
        """查詢某檔股票在某一分點的逐日買賣超時序，含累計買賣超與連買／連賣天數。

        用來判斷一個分點是在這檔股票上持續加碼還是在出貨。

        Args:
            stock_id: 股票代號，例如 "1476"
            branch: 分點代號（區分大小寫）或名稱關鍵字，例如 "9600" 或 "富邦"
            start_date: 起始日 YYYY-MM-DD 或 YYYYMMDD（選填，留空代表資料最早日）
            end_date: 結束日（選填，留空代表資料最新日）
            limit: 最多顯示幾個交易日（預設 60，顯示最近的 N 天；區間合計與連買天數
                仍以整個區間計算）

        Returns:
            逐日買／賣張數、買賣超、累計買賣超與買賣均價，另附區間合計與連買／連賣天數
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        stock_id = (stock_id or "").strip()
        if not stock_is_covered(db, stock_id):
            return MSG_BRANCH_STOCK_NOT_COVERED.format(stock_id=stock_id)

        resolved = resolve_branch(db, branch)
        if isinstance(resolved, str):
            return resolved

        window = resolve_date_range(db, start_date, end_date, default_days=0)
        if isinstance(window, str):
            return window
        start, end = window

        rows = db.query(TREND_SQL, (stock_id, resolved.code, start, end), max_rows=2000)
        if not rows:
            return (
                f"分點 {resolved.label} 在 {format_date(start)} ~ {format_date(end)} 期間"
                f"沒有 {stock_id} 的進出紀錄。"
            )

        total_buy = sum_field(rows, "buy_vol")
        total_sell = sum_field(rows, "sell_vol")
        total_buy_amt = sum_field(rows, "buy_amt")
        total_sell_amt = sum_field(rows, "sell_amt")
        net_total = total_buy - total_sell
        direction, streak = trailing_streak([r.get("net_vol") for r in rows])

        lines = [
            f"{stock_id} × {resolved.label} 逐日進出 "
            f"{format_date(rows[0]['trade_date'])} ~ {format_date(rows[-1]['trade_date'])}，"
            f"共 {len(rows):,} 個交易日",
            f"區間合計：買 {format_lots(total_buy)} 張 / 賣 {format_lots(total_sell)} 張，"
            f"買賣超 {format_lots_signed(net_total)} 張，"
            f"買進均價 {format_avg_price(total_buy_amt, total_buy)}"
            f" / 賣出均價 {format_avg_price(total_sell_amt, total_sell)}",
        ]
        lines.append(
            f"目前連{direction} {streak} 天" if streak else "最後一個交易日無買賣超（或未交易）"
        )

        # Cumulative net runs over the whole range, so a truncated view still shows
        # the true running total rather than one restarted at the display window.
        cumulative = 0
        rendered = []
        for row in rows:
            cumulative += int(row.get("net_vol") or 0)
            rendered.append(
                f"- {format_date(row['trade_date'])}  "
                f"買 {format_lots(row.get('buy_vol'))} / 賣 {format_lots(row.get('sell_vol'))} 張，"
                f"買賣超 {format_lots_signed(row.get('net_vol'))} 張"
                f"（累計 {format_lots_signed(cumulative)} 張）"
                f"買均價 {format_avg_price(row.get('buy_amt'), row.get('buy_vol'))}"
                f" / 賣均價 {format_avg_price(row.get('sell_amt'), row.get('sell_vol'))}"
            )

        lines.append("")
        if len(rendered) > limit:
            lines.append(f"（僅顯示最近 {limit} 個交易日，共 {len(rendered):,} 天）")
            rendered = rendered[-limit:]
        lines.extend(rendered)
        lines.append("\n說明：數量單位為「張」（1 張 = 1000 股）；累計買賣超由區間起始日累加。")
        return "\n".join(lines)
