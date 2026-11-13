"""分點進出資料庫的 contract test。

Like the other live tests in this directory, the only job here is to catch an
interface change that would break our tools — a table or column the branch tools
read with a hardcoded name being renamed, retyped or dropped by a change to
``branch_trades_schema.sql`` or to the import pipeline. It deliberately does **not**
assert that the database has data for any particular stock or day: what is loaded is
up to the user's own import runs, and an empty table is not a schema break.

Skipped entirely when ``BRANCH_DB_URL`` is unset, which is the normal state in CI —
the credentials are the user's own and are not available to the scheduled run.
"""

import pytest

from utils.config import BranchDBConfig
from utils.neon_db import get_branch_db

pytestmark = pytest.mark.skipif(
    not BranchDBConfig.URL, reason="BRANCH_DB_URL 未設定，略過分點資料庫 contract test"
)

# Every column the branch tools name explicitly. Keep this in step with the SQL in
# utils/branch_query.py and tools/branch/*.py — that is the point of the test.
REQUIRED_COLUMNS = {
    "brokers": {"broker_code", "broker_name"},
    "broker_branches": {
        "branch_code",
        "branch_name",
        "broker_code",
        "first_seen",
        "last_seen",
        "updated_at",
    },
    "stocks": {"stock_id", "stock_name", "market"},
    "branch_daily_trades": {
        "trade_date",
        "stock_id",
        "branch_code",
        "price",
        "buy_vol",
        "sell_vol",
    },
    "branch_stock_daily": {
        "trade_date",
        "stock_id",
        "branch_code",
        "buy_vol",
        "sell_vol",
        "buy_amt",
        "sell_amt",
        "net_vol",
    },
    "import_log": {"trade_date", "stock_id", "row_count", "total_vol"},
}


@pytest.fixture(scope="module")
def db():
    return get_branch_db()


@pytest.mark.parametrize("table, columns", sorted(REQUIRED_COLUMNS.items()))
def test_hardcoded_columns_exist(db, table, columns):
    rows = db.query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
        cache_ttl=0,
        max_rows=200,
    )
    assert rows, f"資料表 {table} 不存在"
    present = {r["column_name"] for r in rows}
    missing = columns - present
    assert not missing, f"{table} 缺少工具會讀取的欄位: {sorted(missing)}"


def test_branch_code_keeps_a_case_sensitive_collation(db):
    """'9A9d' 永豐古亭 與 '9A9D' 永豐忠孝 必須是不同的鍵。

    schema 用 ``COLLATE "C"`` 達成這件事。若日後改成大小寫不敏感的 collation，
    ``WHERE branch_code = %s`` 會把兩個分點混成一個，而且不會有任何錯誤。
    """
    row = db.query_one(
        """
        SELECT ('9A9d' = '9A9D' COLLATE "C") AS folded
        """,
        cache_ttl=0,
    )
    assert row is not None and row["folded"] is False

    rows = db.query(
        """
        SELECT collation_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name IN ('broker_branches', 'branch_daily_trades', 'branch_stock_daily')
          AND column_name = 'branch_code'
        """,
        cache_ttl=0,
    )
    assert rows, "找不到 branch_code 欄位"
    assert all(r["collation_name"] == "C" for r in rows), (
        "branch_code 的 collation 不再是 C，大小寫不同的分點會被視為同一個: "
        f"{[r['collation_name'] for r in rows]}"
    )


def test_net_vol_is_still_derived_from_buy_minus_sell(db):
    """工具直接採用 net_vol，不自己算，所以它的定義必須沒變。"""
    row = db.query_one(
        """
        SELECT trade_date, stock_id, branch_code, buy_vol, sell_vol, net_vol
        FROM branch_stock_daily
        LIMIT 1
        """,
        cache_ttl=0,
    )
    if row is None:
        pytest.skip("branch_stock_daily 目前沒有資料")
    assert row["net_vol"] == row["buy_vol"] - row["sell_vol"]


def test_rollup_agrees_with_the_price_level_detail(db):
    """彙總表必須是明細表的加總，否則工具報的張數與均價都會悄悄失真。"""
    row = db.query_one(
        "SELECT trade_date, stock_id FROM branch_stock_daily ORDER BY trade_date DESC LIMIT 1",
        cache_ttl=0,
    )
    if row is None:
        pytest.skip("branch_stock_daily 目前沒有資料")

    detail = db.query_one(
        """
        SELECT sum(buy_vol)         AS buy_vol,
               sum(sell_vol)        AS sell_vol,
               sum(price * buy_vol) AS buy_amt
        FROM branch_daily_trades
        WHERE trade_date = %s AND stock_id = %s
        """,
        (row["trade_date"], row["stock_id"]),
        cache_ttl=0,
    )
    if detail is None or detail["buy_vol"] is None:
        pytest.skip("該日明細資料不存在（只匯入了彙總）")

    rollup = db.query_one(
        """
        SELECT sum(buy_vol)  AS buy_vol,
               sum(sell_vol) AS sell_vol,
               sum(buy_amt)  AS buy_amt
        FROM branch_stock_daily
        WHERE trade_date = %s AND stock_id = %s
        """,
        (row["trade_date"], row["stock_id"]),
        cache_ttl=0,
    )
    assert rollup["buy_vol"] == detail["buy_vol"]
    assert rollup["sell_vol"] == detail["sell_vol"]
    assert rollup["buy_amt"] == detail["buy_amt"]


def test_coverage_tool_runs_against_the_live_database():
    """工具層的 smoke test：不斷言內容，只確認整條路徑跑得通。"""
    import tools.branch.reference as reference
    from tests.helpers import register_module_tools

    out = register_module_tools(reference)["get_branch_data_coverage"]()
    assert isinstance(out, str) and out
    assert not out.startswith("查詢失敗"), out
