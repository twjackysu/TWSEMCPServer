"""分點進出資料庫工具的 offline 測試（不連資料庫、不打網路）。

資料庫層用 :class:`FakeBranchDB` 取代，只替換 ``query`` / ``write_transaction``，
所以工具自己的日期預設、分點解析、排序、分頁、張數換算與訊息選擇都照常執行。

這裡的斷言分兩類：

* **呈現與算法**：張數換算（資料庫存股、輸出張）、期間加權均價（Σ金額 ÷ Σ股數，
  不是每日均價再平均）、連買天數、分頁邊界。
* **訊息要分得開**：「未設定連線」「資料庫未收錄這檔股票」「這天沒資料」
  「broker_code 未回填」是四種不同狀況，混成一句的話呼叫端會把「沒收錄」讀成
  「沒人買賣」。每一種都有獨立斷言。

券商對應演算法（``utils/broker_mapping.py``）的邊界案例也在這裡，因為它們全部來自
實測到的上游資料怪癖：臺/台不一致、HTML entity、三種破折號、總公司名稱比分公司
前綴長、已停用的分點。
"""

from datetime import date
from decimal import Decimal

import pytest

import tools.branch.backfill as backfill
import tools.branch.by_branch as by_branch
import tools.branch.by_stock as by_stock
import tools.branch.reference as reference
import utils.neon_db as neon_db
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from utils.branch_format import (
    format_avg_price,
    format_lots,
    format_lots_signed,
    parse_trade_date,
    trailing_streak,
)
from utils.broker_mapping import resolve_broker_mapping
from utils.constants import (
    MSG_BRANCH_DB_NOT_CONFIGURED,
    MSG_BRANCH_NOT_FOUND,
)

pytestmark = pytest.mark.offline

TRADE_DATE = date(2026, 11, 13)


class FakeBranchDB:
    """Stands in for :class:`utils.neon_db.BranchDB`.

    ``routes`` maps a distinctive fragment of a SQL statement to the rows it should
    return (or a callable taking the bound parameters). An unrouted statement fails
    the test rather than quietly returning nothing, so a changed query cannot slip
    through as "no data".
    """

    def __init__(self, routes=None, configured=True, write_configured=True):
        self.routes = routes or {}
        self._configured = configured
        self._write_configured = write_configured
        self.queries = []
        self.transactions = []

    @property
    def configured(self):
        return self._configured

    @property
    def write_configured(self):
        return self._write_configured

    def query(self, sql, params=(), *, cache_ttl=None, max_rows=None):
        self.queries.append((sql, tuple(params)))
        for needle, value in self.routes.items():
            if needle in sql:
                rows = value(tuple(params)) if callable(value) else value
                return [dict(row) for row in rows]
        raise AssertionError(f"FakeBranchDB 沒有設定此查詢的路由:\n{sql}")

    def query_one(self, sql, params=(), *, cache_ttl=None):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def write_transaction(self, statements):
        self.transactions.append(list(statements))
        return [len(s.params) if s.many else 1 for s in statements]

    def clear_cache(self):
        pass


@pytest.fixture
def db(monkeypatch):
    """Install a FakeBranchDB as the process-wide instance; tests fill in routes."""
    fake = FakeBranchDB()
    monkeypatch.setattr(neon_db, "_instance", fake)
    return fake


def tools_of(module, client=None):
    return register_module_tools(module, client or OfflineClient({}))


# --------------------------------------------------------------- 呈現與算法


@pytest.mark.parametrize(
    "shares, expected",
    [
        (597361, "597.361"),   # 零股精度必須保留
        (356000, "356"),       # 整張不帶小數點
        (352084, "352.084"),
        (1, "0.001"),          # 一股
        (0, "0"),
        (None, "-"),
        (-558490, "-558.49"),
        (1234567890, "1,234,567.89"),
        (Decimal("597361"), "597.361"),
    ],
)
def test_format_lots_converts_shares_to_lots(shares, expected):
    assert format_lots(shares) == expected


def test_format_lots_signed_always_carries_direction():
    assert format_lots_signed(558490) == "+558.49"
    assert format_lots_signed(-558490) == "-558.49"
    assert format_lots_signed(0) == "0"


def test_avg_price_is_amount_over_volume():
    # 富邦 1476 2026-11-13: 229,107,253 / 597,361 股
    assert format_avg_price(229107253, 597361) == "383.53"


def test_avg_price_with_no_volume_is_not_zero_and_does_not_raise():
    """只買沒賣的分點 sell_vol = 0，必須顯示 '-' 而不是 0 或除零錯誤."""
    assert format_avg_price(0, 0) == "-"
    assert format_avg_price(Decimal("0.00"), 0) == "-"
    assert format_avg_price(None, 100) == "-"


def test_trailing_streak_counts_back_from_the_latest_day():
    assert trailing_streak([-100, 500, 300, 200]) == ("買", 3)
    assert trailing_streak([100, -500, -300]) == ("賣", 2)
    # 買賣超 0 既不是連買也不是連賣，必須中斷
    assert trailing_streak([500, 0]) == ("", 0)
    assert trailing_streak([]) == ("", 0)


@pytest.mark.parametrize("raw", ["2026-11-13", "20261113", "2026/11/13"])
def test_parse_trade_date_accepts_the_formats_other_tools_take(raw):
    assert parse_trade_date(raw) == TRADE_DATE


def test_parse_trade_date_rejects_ambiguous_input():
    with pytest.raises(ValueError):
        parse_trade_date("13/11/2026")


# ------------------------------------------------- 未設定連線時每支工具都要講清楚


@pytest.mark.parametrize(
    "module, calls",
    [
        (reference, [("get_branch_data_coverage", {}), ("search_broker_branch", {"keyword": "富邦"})]),
        (
            by_stock,
            [
                ("get_stock_branch_summary", {"stock_id": "1476"}),
                ("get_stock_price_detail", {"stock_id": "1476"}),
                ("get_stock_branch_trend", {"stock_id": "1476", "branch": "9600"}),
            ],
        ),
        (
            by_branch,
            [
                ("get_branch_stock_ranking", {"branch": "9600"}),
                ("get_branch_daily_history", {"branch": "9600"}),
            ],
        ),
        (backfill, [("backfill_branch_reference_data", {})]),
    ],
)
def test_every_tool_reports_missing_configuration(monkeypatch, module, calls):
    monkeypatch.setattr(neon_db, "_instance", FakeBranchDB(configured=False))
    registered = tools_of(module)
    for name, kwargs in calls:
        assert registered[name](**kwargs) == MSG_BRANCH_DB_NOT_CONFIGURED, name


def test_all_eight_tools_are_registered():
    names = set()
    for module in (reference, by_stock, by_branch, backfill):
        names |= set(tools_of(module))
    assert names == {
        "get_branch_data_coverage",
        "search_broker_branch",
        "get_stock_branch_summary",
        "get_stock_price_detail",
        "get_stock_branch_trend",
        "get_branch_stock_ranking",
        "get_branch_daily_history",
        "backfill_branch_reference_data",
    }


# ------------------------------------------------------------ 四種空資料訊息


def test_uncovered_stock_is_not_reported_as_no_trading(db):
    """資料庫沒收錄的股票必須說「未收錄」，不能讓呼叫端讀成「沒人買賣」."""
    db.routes = {"FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": []}
    out = tools_of(by_stock)["get_stock_branch_summary"](stock_id="2330")
    assert "未收錄" in out
    assert "2330" in out
    assert "get_branch_data_coverage" in out


def test_covered_stock_with_no_rows_on_that_date(db):
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "d.branch_code      AS code": [],
    }
    out = tools_of(by_stock)["get_stock_branch_summary"](stock_id="1476", date="20261113")
    assert "2026-11-13" in out
    assert "沒有分點進出資料" in out
    assert "未收錄" not in out


def test_broker_grouping_says_mapping_is_missing(db):
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "count(broker_code) AS mapped": [{"mapped": 0}],
    }
    out = tools_of(by_stock)["get_stock_branch_summary"](
        stock_id="1476", date="20261113", group_by="broker"
    )
    assert "broker_code" in out
    assert "backfill_branch_reference_data" in out


def test_unknown_branch_points_at_the_search_tool(db):
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "WHERE b.branch_code = %s": [],
        "WHERE b.branch_name ILIKE %s": [],
    }
    out = tools_of(by_stock)["get_stock_branch_trend"](stock_id="1476", branch="不存在")
    assert out == MSG_BRANCH_NOT_FOUND.format(keyword="不存在")


# ------------------------------------------------------------------ 分點解析


def test_branch_code_lookup_is_case_sensitive(db):
    """'9A9d' 永豐古亭 與 '9A9D' 永豐忠孝 是不同分點，查詢必須原樣送進 SQL."""
    branches = {
        "9A9d": {"branch_code": "9A9d", "branch_name": "永豐古亭", "broker_code": None, "broker_name": None},
        "9A9D": {"branch_code": "9A9D", "branch_name": "永豐忠孝", "broker_code": None, "broker_name": None},
    }
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "WHERE b.branch_code = %s": lambda params: (
            [branches[params[0]]] if params[0] in branches else []
        ),
        "SELECT min(trade_date) AS d_min, max(trade_date) AS d_max FROM branch_stock_daily": [
            {"d_min": date(2026, 9, 18), "d_max": TRADE_DATE}
        ],
        "WHERE stock_id = %s AND branch_code = %s AND trade_date BETWEEN": [
            {
                "trade_date": TRADE_DATE,
                "buy_vol": 1000,
                "sell_vol": 0,
                "buy_amt": Decimal("383000"),
                "sell_amt": Decimal("0"),
                "net_vol": 1000,
            }
        ],
    }
    trend = tools_of(by_stock)["get_stock_branch_trend"]
    assert "永豐古亭" in trend(stock_id="1476", branch="9A9d")
    assert "永豐忠孝" in trend(stock_id="1476", branch="9A9D")


def test_ambiguous_branch_name_lists_candidates_instead_of_guessing(db):
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "WHERE b.branch_code = %s": [],
        "WHERE b.branch_name ILIKE %s": [
            {"branch_code": "9621", "branch_name": "富邦內湖", "broker_code": None, "broker_name": None},
            {"branch_code": "9623", "branch_name": "富邦台北", "broker_code": None, "broker_name": None},
        ],
    }
    out = tools_of(by_stock)["get_stock_branch_trend"](stock_id="1476", branch="富邦")
    assert "9621" in out and "9623" in out
    assert "區分大小寫" in out


def test_exact_branch_name_breaks_the_tie(db):
    """「富邦」要解析成總公司 9600，而不是因為 富邦台北 等分點而回報模稜兩可."""
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "WHERE b.branch_code = %s": [],
        "WHERE b.branch_name ILIKE %s": [
            {"branch_code": "9600", "branch_name": "富邦", "broker_code": None, "broker_name": None},
            {"branch_code": "9623", "branch_name": "富邦台北", "broker_code": None, "broker_name": None},
        ],
        "SELECT min(trade_date) AS d_min, max(trade_date) AS d_max FROM branch_stock_daily": [
            {"d_min": date(2026, 9, 18), "d_max": TRADE_DATE}
        ],
        "WHERE stock_id = %s AND branch_code = %s AND trade_date BETWEEN": lambda params: (
            [
                {
                    "trade_date": TRADE_DATE,
                    "buy_vol": 597361,
                    "sell_vol": 38871,
                    "buy_amt": Decimal("229107253"),
                    "sell_amt": Decimal("14652124"),
                    "net_vol": 558490,
                }
            ]
            if params[1] == "9600"
            else []
        ),
    }
    out = tools_of(by_stock)["get_stock_branch_trend"](stock_id="1476", branch="富邦")
    assert "富邦 (9600)" in out


# --------------------------------------------------------- 個股某日分點買賣超


def _summary_rows():
    return [
        {
            "code": "9600", "name": "富邦",
            "buy_vol": 597361, "sell_vol": 38871,
            "buy_amt": Decimal("229107253.00"), "sell_amt": Decimal("14652124.00"),
            "net_vol": 558490,
        },
        {
            "code": "1360", "name": "港麥格理",
            "buy_vol": 356000, "sell_vol": 0,
            "buy_amt": Decimal("135540500.00"), "sell_amt": Decimal("0.00"),
            "net_vol": 356000,
        },
        {
            "code": "8440", "name": "摩根大通",
            "buy_vol": 0, "sell_vol": 500000,
            "buy_amt": Decimal("0.00"), "sell_amt": Decimal("190000000.00"),
            "net_vol": -500000,
        },
    ]


@pytest.fixture
def summary_db(db):
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "SELECT max(trade_date) AS d FROM branch_stock_daily WHERE stock_id": [{"d": TRADE_DATE}],
        "d.branch_code      AS code": _summary_rows(),
    }
    return db


def test_summary_defaults_to_the_latest_date_for_that_stock(summary_db):
    out = tools_of(by_stock)["get_stock_branch_summary"](stock_id="1476")
    assert "2026-11-13" in out
    assert any(
        "max(trade_date) AS d FROM branch_stock_daily WHERE stock_id" in sql
        for sql, _ in summary_db.queries
    )


def test_summary_shows_both_directions_and_lots(summary_db):
    out = tools_of(by_stock)["get_stock_branch_summary"](stock_id="1476")
    assert "買超前" in out and "賣超前" in out
    assert "富邦 (9600)" in out and "摩根大通 (8440)" in out
    # 張，不是股
    assert "+558.49 張" in out
    assert "597.361" in out
    assert "597,361" not in out
    # 只買沒賣的分點，賣均價必須是 '-'
    assert "賣均價 -" in out


def test_summary_collapses_the_whole_market_total_to_one_figure(db):
    """涵蓋全市場時買量＝賣量、買金額＝賣金額，合計只該出現一個成交量與一個均價。

    實測 1476 2026-11-13：638 個分點加總後買賣兩邊都是 4,050,953 股、金額也相同，
    印成「買 4,050.953 張 / 賣 4,050.953 張，買均價 379.30 / 賣均價 379.30」
    會讓呼叫端把同一個數字讀成兩個。
    """
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "SELECT max(trade_date) AS d FROM branch_stock_daily WHERE stock_id": [{"d": TRADE_DATE}],
        "d.branch_code      AS code": [
            {
                "code": "9600", "name": "富邦",
                "buy_vol": 600000, "sell_vol": 400000,
                "buy_amt": Decimal("228000000"), "sell_amt": Decimal("152000000"),
                "net_vol": 200000,
            },
            {
                "code": "8440", "name": "摩根大通",
                "buy_vol": 400000, "sell_vol": 600000,
                "buy_amt": Decimal("152000000"), "sell_amt": Decimal("228000000"),
                "net_vol": -200000,
            },
        ],
    }
    out = tools_of(by_stock)["get_stock_branch_summary"](stock_id="1476")
    # 第二行是合計行；只斷言這一行，個別分點那幾行本來就該有買/賣兩欄
    assert out.splitlines()[1] == "全日成交 1,000 張，成交均價 380.00"
    assert "合計：" not in out
    # 個別分點的買賣兩側仍然要分開顯示
    assert "買 600 / 賣 400 張" in out


def test_summary_keeps_both_sides_when_the_rows_are_a_subset(summary_db):
    """只涵蓋部分分點時（例如 broker_code 只回填了一部分），兩側確實不同，要照實印。"""
    out = tools_of(by_stock)["get_stock_branch_summary"](stock_id="1476")
    assert "合計：買 953.361 張 / 賣 538.871 張" in out
    assert "全日成交" not in out


def test_summary_single_direction_respects_limit_and_offset(summary_db):
    out = tools_of(by_stock)["get_stock_branch_summary"](
        stock_id="1476", side="buy", limit=1, offset=1
    )
    assert "港麥格理" in out
    assert "富邦 (9600)" not in out


def test_summary_rejects_unknown_side_and_group_by(summary_db):
    registered = tools_of(by_stock)["get_stock_branch_summary"]
    assert "side 只接受" in registered(stock_id="1476", side="往上")
    assert "group_by 只接受" in registered(stock_id="1476", group_by="firm")


# ----------------------------------------------------------------- 分價量表


def test_price_detail_requires_a_branch_for_branch_grouping(db):
    db.routes = {"FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}]}
    out = tools_of(by_stock)["get_stock_price_detail"](stock_id="1476", group_by="branch")
    assert "需要同時指定 branch" in out
    # 沒有分點時不得真的去打明細表（單日可達數千列）
    assert not any("FROM branch_daily_trades" in sql for sql, _ in db.queries)


def test_whole_market_price_detail_reports_one_volume_per_price(db):
    """全市場同一價位的買量與賣量必然相等（買進的那一股就是賣出的那一股）。

    實測 1476 2026-11-13 每個價位的 buy_vol 與 sell_vol 完全相同，所以印成
    「買 7.422 張 / 賣 7.422 張」會讓呼叫端誤以為是兩個獨立數字。
    """
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "SELECT max(trade_date) AS d FROM branch_stock_daily WHERE stock_id": [{"d": TRADE_DATE}],
        "FROM branch_daily_trades": [
            {"price": Decimal("390.00"), "buy_vol": 7422, "sell_vol": 7422, "branches": 30},
            {"price": Decimal("389.50"), "buy_vol": 16169, "sell_vol": 16169, "branches": 24},
        ],
    }
    out = tools_of(by_stock)["get_stock_price_detail"](stock_id="1476")
    assert "390.00" in out and "389.50" in out
    assert "成交 7.422 張（30 個分點）" in out
    assert "合計成交 23.591 張" in out
    assert "買 7.422" not in out
    # 高價排在前
    assert out.index("390.00") < out.index("389.50")


def test_single_branch_price_detail_splits_buy_and_sell(db):
    """單一分點在同一價位可以只買或只賣，這時買賣兩欄才有意義。"""
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "SELECT max(trade_date) AS d FROM branch_stock_daily WHERE stock_id": [{"d": TRADE_DATE}],
        "WHERE b.branch_code = %s": [
            {"branch_code": "9600", "branch_name": "富邦", "broker_code": None, "broker_name": None}
        ],
        "AND branch_code = %s": [
            {"price": Decimal("390.00"), "buy_vol": 120000, "sell_vol": 0, "branches": 1},
            {"price": Decimal("389.50"), "buy_vol": 0, "sell_vol": 31000, "branches": 1},
        ],
    }
    out = tools_of(by_stock)["get_stock_price_detail"](stock_id="1476", branch="9600")
    assert "富邦 (9600)" in out
    assert "買 120 張 / 賣 0 張" in out
    assert "合計：買 120 張 / 賣 31 張" in out


def test_price_detail_offset_past_the_end_says_so(db):
    db.routes = {
        "FROM branch_stock_daily WHERE stock_id = %s LIMIT 1": [{"present": 1}],
        "SELECT max(trade_date) AS d FROM branch_stock_daily WHERE stock_id": [{"d": TRADE_DATE}],
        "FROM branch_daily_trades": [
            {"price": Decimal("385.00"), "buy_vol": 1000, "sell_vol": 0, "branches": 1}
        ],
    }
    out = tools_of(by_stock)["get_stock_price_detail"](stock_id="1476", offset=50)
    assert "offset=50 已超出範圍" in out


# --------------------------------------------------------------- 分點期間排行


def test_branch_ranking_uses_period_weighted_average_price(db):
    """期間均價必須是 Σ金額 ÷ Σ股數，不是每日均價的平均."""
    db.routes = {
        "WHERE b.branch_code = %s": [
            {"branch_code": "9600", "branch_name": "富邦", "broker_code": None, "broker_name": None}
        ],
        "LIMIT %s": [{"d_min": date(2026, 10, 16), "d_max": TRADE_DATE}],
        "WHERE d.branch_code = %s AND d.trade_date BETWEEN": [
            {
                "stock_id": "1476",
                "stock_name": "儒鴻",
                # 1 張 @ 100 元 + 999 張 @ 400 元 → 加權均價 399.70，每日均價平均會是 250
                "buy_vol": 1000000,
                "sell_vol": 0,
                "buy_amt": Decimal("399700000.00"),
                "sell_amt": Decimal("0.00"),
                "net_vol": 1000000,
                "days": 2,
            }
        ],
    }
    out = tools_of(by_branch)["get_branch_stock_ranking"](branch="9600")
    assert "買均價 399.7" in out
    assert "250" not in out
    assert "有交易 2 天" in out
    assert "期間加權均價" in out


def test_branch_ranking_defaults_to_the_last_20_trading_days(db):
    db.routes = {
        "WHERE b.branch_code = %s": [
            {"branch_code": "9600", "branch_name": "富邦", "broker_code": None, "broker_name": None}
        ],
        "LIMIT %s": [{"d_min": date(2026, 10, 16), "d_max": TRADE_DATE}],
        "WHERE d.branch_code = %s AND d.trade_date BETWEEN": [],
    }
    tools_of(by_branch)["get_branch_stock_ranking"](branch="9600")
    window = [params for sql, params in db.queries if "LIMIT %s" in sql]
    assert window and window[0] == (20,), "預設區間應取最近 20 個『交易日』而非日曆天"


def test_branch_daily_history_paginates(db):
    rows = [
        {
            "trade_date": date(2026, 11, 13 - i),
            "stock_id": "1476",
            "stock_name": "儒鴻",
            "buy_vol": 1000 * (i + 1),
            "sell_vol": 0,
            "buy_amt": Decimal(383 * 1000 * (i + 1)),
            "sell_amt": Decimal(0),
            "net_vol": 1000 * (i + 1),
        }
        for i in range(5)
    ]
    db.routes = {
        "WHERE b.branch_code = %s": [
            {"branch_code": "9600", "branch_name": "富邦", "broker_code": None, "broker_name": None}
        ],
        "LIMIT %s": [{"d_min": date(2026, 11, 9), "d_max": TRADE_DATE}],
        "WHERE d.branch_code = %s AND d.trade_date BETWEEN": rows,
    }
    history = tools_of(by_branch)["get_branch_daily_history"]
    out = history(branch="9600", limit=2)
    assert "顯示第 1–2 筆" in out
    assert "offset=2 查看更多" in out
    assert "offset=99 已超出範圍" in history(branch="9600", offset=99)


# -------------------------------------------------------------- 覆蓋範圍工具


def test_coverage_warns_when_reference_tables_are_empty(db):
    db.routes = {
        "SELECT (SELECT count(*) FROM broker_branches)": [
            {
                "branches": 804, "branches_mapped": 0, "brokers": 0, "stocks": 0,
                "d_min": date(2026, 9, 18), "d_max": TRADE_DATE, "days": 34,
            }
        ],
        "LEFT JOIN stocks s ON s.stock_id = d.stock_id\nGROUP BY d.stock_id": [
            {
                "stock_id": "1476", "stock_name": None, "market": None,
                "d_min": date(2026, 9, 18), "d_max": TRADE_DATE,
                "days": 34, "row_count": 15852,
                "buy_vol": 3245678, "sell_vol": 3245678,
            }
        ],
    }
    out = tools_of(reference)["get_branch_data_coverage"]()
    assert "共收錄 1 檔股票" in out
    assert "2026-09-18 ~ 2026-11-13" in out
    # broker_code 與 stocks 都是空的，必須主動說出來而不是讓呼叫端自己發現
    assert "broker_code 尚未回填" in out
    assert "stocks 主檔為空" in out
    assert "1 張 = 1000 股" in out


def test_coverage_per_stock_flags_unbalanced_buy_sell(db):
    """匯入流程會驗 Σbuy = Σsell；不相等代表那天的彙總不可信，要標出來."""
    db.routes = {
        "LEFT JOIN import_log l": [
            {
                "trade_date": TRADE_DATE, "branches": 638,
                "buy_vol": 3245678, "sell_vol": 3245000,
                "import_rows": 3494, "import_vol": 3245678,
            }
        ]
    }
    out = tools_of(reference)["get_branch_data_coverage"](stock_id="1476")
    assert "⚠" in out
    assert "買賣量不相等" in out


def test_search_branch_warns_about_case_sensitivity(db):
    db.routes = {
        "WHERE b.branch_name ILIKE %s OR b.branch_code ILIKE %s": [
            {
                "branch_code": "9A9d", "branch_name": "永豐古亭",
                "broker_code": None, "broker_name": None,
                "first_seen": date(2026, 9, 18), "last_seen": TRADE_DATE,
            }
        ]
    }
    out = tools_of(reference)["search_broker_branch"](keyword="永豐")
    assert "9A9d" in out
    assert "代號區分大小寫" in out


# ---------------------------------------------------- 券商對應演算法邊界案例


HQ_ROWS = [
    ("1020", "合庫"),
    ("1030", "土銀"),
    ("1040", "臺銀證券"),      # 名稱比分公司前綴長
    ("1110", "台灣企銀"),      # 來源寫「臺灣企銀」
    ("1360", "港商麥格理"),    # 來源寫「香港商麥格里」
    ("6110", "台中銀"),        # 來源寫「台中商銀」
    # 真實名稱是「群益金鼎」，比分點名稱「群益天母」長，所以第 2 階段（既有分點
    # 名稱前綴）比不到，918P 只能靠第 3 階段的兄弟代號。這裡照實際資料設定，否則
    # 第 3 階段永遠不會被這組案例觸發。
    ("9100", "群益金鼎"),
    ("9600", "富邦"),
]

BRANCH_ROWS = [
    ("1021", "合庫- 台中"),            # 半形空白
    ("1031", "土銀-台中"),             # 同前綴 10 但不同券商
    ("1042", "臺銀-台南"),             # 總公司名稱較長
    ("111E", "臺灣企銀-桃園"),         # 臺 vs 台
    ("136T", "香港商麥格里--自營"),    # 兩個破折號且名稱對不上
    ("611T", "台中商銀－自營"),        # 全形破折號且名稱對不上
    ("6012", "&#29319;亞-台中"),       # HTML entity（犇亞），總公司不在清單內
    ("9183", "群益-高雄"),
    ("9623", "富邦-台北"),
    ("961H", "富邦-新板"),
    ("888B", "富邦證券股份有限公司"),  # 無破折號，全名
]

DB_BRANCHES = {
    "1020": "合庫", "1021": "合庫台中",
    "1030": "土銀", "1031": "土銀台中",
    "1040": "臺銀證券", "1042": "臺銀台南",
    "1110": "企銀", "111E": "企銀桃園",
    "9100": "群益", "9183": "群益高雄",
    "918P": "群益天母",   # 已停用，來源查不到
    "9600": "富邦", "9623": "富邦台北", "961H": "富邦新板",
}


@pytest.fixture(scope="module")
def mapping():
    return resolve_broker_mapping(BRANCH_ROWS, HQ_ROWS, DB_BRANCHES)


@pytest.mark.parametrize(
    "branch_code, broker_code, why",
    [
        ("9623", "9600", "富邦台北 → 富邦"),
        ("961H", "9600", "富邦新板 → 富邦（代號第二碼不同仍同券商）"),
        ("1021", "1020", "合庫台中 → 合庫"),
        ("1031", "1030", "土銀台中 → 土銀，不能因為同前綴 10 併進合庫"),
        ("1042", "1040", "臺銀-台南 → 臺銀證券（總公司名稱比前綴長）"),
        ("111E", "1110", "臺灣企銀 vs 台灣企銀（臺/台 必須正規化）"),
        ("888B", "9600", "無破折號的全名 → 以最長總公司名稱前綴比對"),
        ("918P", "9100", "已停用分點 → 兄弟代號一致才繼承"),
        ("9600", "9600", "總公司本身"),
    ],
)
def test_broker_mapping_known_cases(mapping, branch_code, broker_code, why):
    assert mapping.mapping.get(branch_code) == broker_code, why


def test_broker_mapping_never_merges_different_firms_sharing_a_prefix(mapping):
    """schema 註解明確警告不能用代號前綴推歸屬：1020 合庫 與 1030 土銀 同前綴 10."""
    assert mapping.mapping["1021"] != mapping.mapping["1031"]


def test_broker_mapping_reports_rather_than_guesses(mapping):
    """名稱比不到總公司的來源列要被列出，不能亂猜."""
    unmatched = {code for code, _ in mapping.unresolved_source}
    assert {"136T", "611T", "6012"} <= unmatched
    # 這些都不在 broker_branches 裡，所以不影響實際可用性
    assert mapping.unresolved_db == []


def test_broker_mapping_leaves_ambiguous_sibling_groups_null():
    """同一個三碼前綴底下的兄弟分點指向兩家券商時，不得硬套其中一家."""
    hq = [("5000", "甲"), ("6000", "乙")]
    branches = [("ABC1", "甲-一號"), ("ABC2", "乙-二號")]
    db_branches = {"ABC1": "甲一號", "ABC2": "乙二號", "ABC9": "不明分點"}
    result = resolve_broker_mapping(branches, hq, db_branches)
    assert result.mapping["ABC1"] == "5000"
    assert result.mapping["ABC2"] == "6000"
    assert "ABC9" not in result.mapping
    assert ("ABC9", "不明分點") in result.unresolved_db


def test_broker_mapping_records_how_each_code_was_resolved(mapping):
    assert mapping.methods["9623"] == "exact"
    assert mapping.methods["1042"] == "hq_name_longer"
    assert mapping.methods["9183"] == "hq_name_longer"
    assert mapping.methods["918P"] == "sibling_prefix"
    assert mapping.methods["9600"] == "headquarters"


def test_broker_mapping_falls_back_to_the_stored_branch_name():
    """來源查不到的分點，若自己的 branch_name 就帶著總公司名稱，應在第 2 階段解決。

    這比第 3 階段的兄弟代號推論直接，所以必須優先，也才不會把能確定的案例
    交給較弱的規則。
    """
    hq = [("9600", "富邦")]
    result = resolve_broker_mapping(
        branch_rows=[],                      # 來源完全沒有這個分點
        hq_rows=hq,
        db_branches={"961Z": "富邦某分點"},
    )
    assert result.mapping["961Z"] == "9600"
    assert result.methods["961Z"] == "db_name_prefix"


# --------------------------------------------------------------- 回填工具


BACKFILL_ROUTES = {
    "/brokerService/brokerList": [{"Code": c, "Name": n} for c, n in HQ_ROWS],
    "/opendata/OpenData_BRK02": [
        {"證券商代號": c, "證券商名稱": n} for c, n in BRANCH_ROWS
    ],
}


@pytest.fixture
def backfill_db(db):
    db.routes = {
        "SELECT branch_code, branch_name, broker_code FROM broker_branches": [
            {"branch_code": code, "branch_name": name, "broker_code": None}
            for code, name in DB_BRANCHES.items()
        ]
    }
    return db


def test_backfill_dry_run_writes_nothing(backfill_db):
    out = tools_of(backfill, OfflineClient(BACKFILL_ROUTES))["backfill_branch_reference_data"](
        target="brokers"
    )
    assert backfill_db.transactions == [], "dry_run 不得開啟寫入 transaction"
    assert "【試算】" in out
    assert "dry_run=False" in out
    assert "個可解析" in out


def test_backfill_reports_unresolved_branches_in_the_dry_run(backfill_db):
    backfill_db.routes = {
        "SELECT branch_code, branch_name, broker_code FROM broker_branches": [
            {"branch_code": "ZZZZ", "branch_name": "無法對應", "broker_code": None}
        ]
    }
    out = tools_of(backfill, OfflineClient(BACKFILL_ROUTES))["backfill_branch_reference_data"](
        target="brokers"
    )
    assert "無法解析的分點" in out
    assert "ZZZZ" in out


def test_backfill_writes_brokers_before_branches_and_touches_nothing_else(backfill_db):
    out = tools_of(backfill, OfflineClient(BACKFILL_ROUTES))["backfill_branch_reference_data"](
        target="brokers", dry_run=False
    )
    assert len(backfill_db.transactions) == 1, "三個語句必須在同一個 transaction"
    statements = backfill_db.transactions[0]
    sqls = [s.sql.strip() for s in statements]
    assert sqls[0].startswith("INSERT INTO brokers"), "brokers 必須先寫（broker_code 有 FK）"
    assert sqls[1].startswith("UPDATE broker_branches")
    joined = " ".join(sqls)
    for forbidden in ("branch_daily_trades", "branch_stock_daily", "import_log"):
        assert forbidden not in joined, f"回填工具不得碰 {forbidden}"
    assert "【實際寫入】" in out


def test_backfill_only_updates_branches_whose_value_changes(backfill_db):
    backfill_db.routes = {
        "SELECT branch_code, branch_name, broker_code FROM broker_branches": [
            {"branch_code": "9623", "branch_name": "富邦台北", "broker_code": "9600"},
            {"branch_code": "961H", "branch_name": "富邦新板", "broker_code": None},
        ]
    }
    tools_of(backfill, OfflineClient(BACKFILL_ROUTES))["backfill_branch_reference_data"](
        target="brokers", dry_run=False
    )
    updates = [s for s in backfill_db.transactions[0] if s.sql.strip().startswith("UPDATE")]
    assert len(updates) == 1
    assert [p[1] for p in updates[0].params] == ["961H"]


def test_backfill_stocks_maps_market_labels(db, monkeypatch):
    class Snap:
        def __init__(self, name, market):
            self.name, self.market = name, market

    monkeypatch.setattr(
        backfill,
        "market_snapshot",
        lambda client: (
            {"2330": Snap("台積電", "上市"), "6488": Snap("環球晶", "上櫃"), "9999": Snap("", "上市")},
            "2026-11-13",
        ),
    )
    out = tools_of(backfill, OfflineClient({}))["backfill_branch_reference_data"](
        target="stocks", dry_run=False
    )
    rows = db.transactions[0][0].params
    assert ("2330", "台積電", "TWSE") in rows
    assert ("6488", "環球晶", "TPEx") in rows
    assert all(code != "9999" for code, _, _ in rows), "沒有名稱的標的要跳過"
    assert "上市 1 / 上櫃 1" in out


def test_backfill_rejects_unknown_target(db):
    out = tools_of(backfill, OfflineClient({}))["backfill_branch_reference_data"](target="everything")
    assert "target 只接受" in out


def test_backfill_refuses_real_write_without_write_credentials(monkeypatch):
    monkeypatch.setattr(
        neon_db, "_instance", FakeBranchDB(configured=True, write_configured=False)
    )
    out = tools_of(backfill, OfflineClient({}))["backfill_branch_reference_data"](dry_run=False)
    assert "BRANCH_DB_WRITE_URL" in out
