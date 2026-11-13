"""Shared lookups for the 分點進出 tools: branch/broker resolution and date defaults.

Every function here takes a :class:`~utils.neon_db.BranchDB` and returns either a
value or, for the resolvers, **a plain string that is already the message to hand
back to the caller** (branch not found, ambiguous name, mapping not back-filled).
The branch tools all return ``str``, so this keeps the "could not pin this down"
paths out of exception handling while still forcing each tool to deal with them.

Case sensitivity: ``branch_code`` is ``COLLATE "C"`` because ``9A9d`` (永豐古亭) and
``9A9D`` (永豐忠孝) are different branches. Code lookups here are therefore exact,
while *name* searches are case-insensitive — a human typing a name should not have to
care, but a code must be passed exactly as the data has it.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple, Union

from .branch_format import format_date, parse_trade_date
from .constants import (
    MSG_BRANCH_AMBIGUOUS,
    MSG_BRANCH_NOT_FOUND,
    MSG_BROKER_MAPPING_MISSING,
)
from .neon_db import BranchDB

# How many candidates to list when a name matches more than one branch
AMBIGUOUS_LIST_LIMIT = 20


@dataclass
class ResolvedBranch:
    """A single 分點."""

    code: str
    name: str
    broker_code: Optional[str] = None
    broker_name: Optional[str] = None

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"


@dataclass
class ResolvedBroker:
    """A 券商總公司 and the branch codes that belong to it."""

    code: str
    name: str
    branch_count: int = 0

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code}) 全系統"


def _escape_like(text: str) -> str:
    """Escape LIKE wildcards so a user's ``%`` matches a literal percent sign."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --------------------------------------------------------------------- coverage


def stock_is_covered(db: BranchDB, stock_id: str) -> bool:
    """True when ``branch_stock_daily`` holds at least one day for this stock."""
    row = db.query_one(
        "SELECT 1 AS present FROM branch_stock_daily WHERE stock_id = %s LIMIT 1",
        (stock_id,),
    )
    return row is not None


def latest_stock_date(db: BranchDB, stock_id: str) -> Optional[date]:
    """The most recent trade date this stock has data for, or None."""
    row = db.query_one(
        "SELECT max(trade_date) AS d FROM branch_stock_daily WHERE stock_id = %s",
        (stock_id,),
    )
    return row["d"] if row and row.get("d") else None


def latest_date(db: BranchDB) -> Optional[date]:
    """The most recent trade date in the database, across all stocks."""
    row = db.query_one("SELECT max(trade_date) AS d FROM branch_stock_daily")
    return row["d"] if row and row.get("d") else None


def recent_trading_range(db: BranchDB, days: int = 20) -> Optional[Tuple[date, date]]:
    """The last ``days`` *trading* days present in the data, as ``(start, end)``.

    Counting trading days rather than subtracting calendar days matters: a 20-calendar
    day window over a long weekend silently covers fewer sessions than asked for.
    """
    rows = db.query(
        """
        SELECT min(trade_date) AS d_min, max(trade_date) AS d_max
        FROM (
            SELECT DISTINCT trade_date
            FROM branch_stock_daily
            ORDER BY trade_date DESC
            LIMIT %s
        ) recent
        """,
        (days,),
        max_rows=1,
    )
    if not rows or not rows[0].get("d_min"):
        return None
    return rows[0]["d_min"], rows[0]["d_max"]


def resolve_date_range(
    db: BranchDB,
    start_date: str,
    end_date: str,
    default_days: int = 20,
) -> Union[Tuple[date, date], str]:
    """Turn optional ``start_date``/``end_date`` strings into a concrete range.

    Both empty → the last ``default_days`` trading days in the data, or the whole
    history when ``default_days`` is 0 or less. One side empty → the other end of the
    available data. Returns an error message on a bad format or a reversed range.
    """
    try:
        start = parse_trade_date(start_date) if start_date else None
        end = parse_trade_date(end_date) if end_date else None
    except ValueError as exc:
        return str(exc)

    if start is None and end is None:
        if default_days > 0:
            window = recent_trading_range(db, default_days)
            if window is None:
                return "分點資料庫目前沒有任何資料。"
            return window
        # default_days <= 0 means "everything we have" (the trend tool wants the
        # whole history so that its cumulative net starts at the real beginning).
        row = db.query_one(
            "SELECT min(trade_date) AS d_min, max(trade_date) AS d_max FROM branch_stock_daily"
        )
        if not row or not row.get("d_min"):
            return "分點資料庫目前沒有任何資料。"
        return row["d_min"], row["d_max"]

    if start is None:
        row = db.query_one("SELECT min(trade_date) AS d FROM branch_stock_daily")
        start = row["d"] if row and row.get("d") else end
    if end is None:
        end = latest_date(db) or start

    if start > end:
        return f"日期範圍顛倒：start_date {format_date(start)} 晚於 end_date {format_date(end)}"
    return start, end


# -------------------------------------------------------------------- resolvers


def resolve_branch(db: BranchDB, keyword: str) -> Union[ResolvedBranch, str]:
    """Find one 分點 from a code (exact, case-sensitive) or a name keyword.

    An exact code wins. Otherwise the name is matched case-insensitively as a
    substring; an exact name match breaks a tie (so ``富邦`` resolves to the 9600
    head office rather than being called ambiguous against 富邦台北 and friends).
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return "請指定分點（代號或名稱關鍵字），例如 branch=\"9600\" 或 branch=\"富邦\""

    row = db.query_one(
        """
        SELECT b.branch_code, b.branch_name, b.broker_code, k.broker_name
        FROM broker_branches b
        LEFT JOIN brokers k ON k.broker_code = b.broker_code
        WHERE b.branch_code = %s
        """,
        (keyword,),
    )
    if row:
        return _branch_from_row(row)

    rows = db.query(
        """
        SELECT b.branch_code, b.branch_name, b.broker_code, k.broker_name
        FROM broker_branches b
        LEFT JOIN brokers k ON k.broker_code = b.broker_code
        WHERE b.branch_name ILIKE %s
        ORDER BY b.branch_code
        """,
        (f"%{_escape_like(keyword)}%",),
        max_rows=200,
    )
    if not rows:
        return MSG_BRANCH_NOT_FOUND.format(keyword=keyword)
    if len(rows) == 1:
        return _branch_from_row(rows[0])

    exact = [r for r in rows if (r.get("branch_name") or "").strip() == keyword]
    if len(exact) == 1:
        return _branch_from_row(exact[0])

    listed = rows[:AMBIGUOUS_LIST_LIMIT]
    candidates = "\n".join(
        f"- {r['branch_code']} {r['branch_name']}" for r in listed
    )
    if len(rows) > len(listed):
        candidates += f"\n...（共 {len(rows)} 個，僅列前 {len(listed)} 個）"
    return MSG_BRANCH_AMBIGUOUS.format(keyword=keyword, candidates=candidates)


def _branch_from_row(row: Dict) -> ResolvedBranch:
    return ResolvedBranch(
        code=row["branch_code"],
        name=row.get("branch_name") or row["branch_code"],
        broker_code=row.get("broker_code"),
        broker_name=row.get("broker_name"),
    )


def broker_mapping_ready(db: BranchDB) -> bool:
    """True when at least one branch has ``broker_code`` filled in."""
    row = db.query_one(
        "SELECT count(broker_code) AS mapped FROM broker_branches",
    )
    return bool(row and row.get("mapped"))


def resolve_broker(db: BranchDB, keyword: str) -> Union[ResolvedBroker, str]:
    """Find one 券商總公司 from its code, its name, or any of its branches.

    Requires ``broker_branches.broker_code`` to have been back-filled; says so
    explicitly otherwise instead of silently returning one branch's numbers.
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return "請指定券商（代號或名稱關鍵字），例如 branch=\"9600\" 或 branch=\"富邦\""
    if not broker_mapping_ready(db):
        return MSG_BROKER_MAPPING_MISSING

    rows = db.query(
        """
        SELECT k.broker_code, k.broker_name, count(b.branch_code) AS branch_count
        FROM brokers k
        LEFT JOIN broker_branches b ON b.broker_code = k.broker_code
        WHERE k.broker_code = %s OR k.broker_name ILIKE %s
        GROUP BY k.broker_code, k.broker_name
        ORDER BY k.broker_code
        """,
        (keyword, f"%{_escape_like(keyword)}%"),
        max_rows=100,
    )
    if len(rows) > 1:
        exact = [r for r in rows if (r.get("broker_name") or "").strip() == keyword]
        rows = exact or rows
    if len(rows) == 1:
        return ResolvedBroker(
            code=rows[0]["broker_code"],
            name=rows[0].get("broker_name") or rows[0]["broker_code"],
            branch_count=int(rows[0].get("branch_count") or 0),
        )
    if len(rows) > 1:
        candidates = "\n".join(f"- {r['broker_code']} {r['broker_name']}" for r in rows[:AMBIGUOUS_LIST_LIMIT])
        return MSG_BRANCH_AMBIGUOUS.format(keyword=keyword, candidates=candidates)

    # Not a firm — try it as a branch and climb to its firm.
    branch = resolve_branch(db, keyword)
    if isinstance(branch, str):
        return branch
    if not branch.broker_code:
        return (
            f"分點 {branch.label} 尚未對應到券商總公司（broker_code 為空）。"
            + MSG_BROKER_MAPPING_MISSING
        )
    row = db.query_one(
        """
        SELECT k.broker_code, k.broker_name, count(b.branch_code) AS branch_count
        FROM brokers k
        LEFT JOIN broker_branches b ON b.broker_code = k.broker_code
        WHERE k.broker_code = %s
        GROUP BY k.broker_code, k.broker_name
        """,
        (branch.broker_code,),
    )
    if not row:
        return ResolvedBroker(code=branch.broker_code, name=branch.broker_code)
    return ResolvedBroker(
        code=row["broker_code"],
        name=row.get("broker_name") or row["broker_code"],
        branch_count=int(row.get("branch_count") or 0),
    )


def branch_codes_of_broker(db: BranchDB, broker_code: str) -> List[str]:
    """Every branch code belonging to one firm."""
    rows = db.query(
        "SELECT branch_code FROM broker_branches WHERE broker_code = %s ORDER BY branch_code",
        (broker_code,),
        max_rows=2000,
    )
    return [r["branch_code"] for r in rows]
