"""集保戶股權分散表 (shareholding distribution by holding size), latest week or a weekly trend.

Two TDCC sources behind one tool, each read through its gateway:
- ``sources.tdcc.opendata``: one CSV with every security for the latest week. One cached request,
  no session -- used for the latest week.
- ``sources.tdcc.qry_stock``: the public query page, one security at a time, any of the last ~51
  weeks, through a stateful form (one POST per week, each with the token the previous reply
  issued). Used for ``weeks`` > 1.

Both agree on levels 1-15 and the total; only 差異數調整 differs, so the trend view never uses it.
"""

import threading
from decimal import Decimal
from typing import Annotated, Dict, List, Optional, Tuple, Union

from fastmcp import FastMCP
from pydantic import Field
from sources.tdcc.levels import LevelHolding
from sources.tdcc.opendata import latest_distribution
from sources.tdcc.qry_stock import StockQuery, WeekDistribution
from toolkit import handle_api_errors
from utils import TWSEAPIClient, plain
from utils.deadline import time_budget

# Each week costs one POST (plus 0.5 s of client throttling), so keep a call to about a quarter.
MAX_WEEKS = 13
MAX_CACHED_WEEKS = 2048
# Time for a trend's requests (utils/deadline.py). 13 weeks normally take under 10 s; each of
# the up to 14 requests may wait 60 s on a slow site.
TREND_BUDGET = 90

# 持股分級 1-17. Levels 1-15 are holding-size brackets in shares (1 張 = 1,000 股),
# 16 is TDCC's 差異數調整 (reconciliation with the share register), 17 is the total.
LEVELS = {
    1: "1-999股",
    2: "1-5張",
    3: "5-10張",
    4: "10-15張",
    5: "15-20張",
    6: "20-30張",
    7: "30-40張",
    8: "40-50張",
    9: "50-100張",
    10: "100-200張",
    11: "200-400張",
    12: "400-600張",
    13: "600-800張",
    14: "800-1000張",
    15: "1000張以上",
    16: "差異數調整",
    17: "合計",
}
BIG_HOLDER_LEVELS = (15,)  # 1000 張以上
BIG_HOLDER_400_LEVELS = (12, 13, 14, 15)
SMALL_HOLDER_LEVELS = (1, 2, 3)  # 10 張以下

Metrics = Dict[str, Union[int, Decimal]]


def _group(levels: List[LevelHolding], keys) -> Tuple[int, Decimal]:
    """(people, % of the depository) of the holding-size levels in ``keys``."""
    present = [h for h in levels if h.level in keys]
    return sum(h.people for h in present), sum((h.pct for h in present), Decimal(0))


def summarize(levels: List[LevelHolding]) -> str:
    """Render one security's level rows plus big/small-holder ratios."""
    by_level = {h.level: h for h in levels}
    lines = []
    for level, label in LEVELS.items():
        h = by_level.get(level)
        if h:
            lines.append(f"{label}: 人數 {h.people:,} | 股數 {h.shares:,} | 占比 {plain(h.pct)}%")
    big_people, big_pct = _group(levels, BIG_HOLDER_LEVELS)
    b400_people, b400_pct = _group(levels, BIG_HOLDER_400_LEVELS)
    small_people, small_pct = _group(levels, SMALL_HOLDER_LEVELS)
    lines.append("")
    lines.append(
        f"千張大戶（1000張以上）: {big_pct:.2f}%（{big_people:,} 人）| "
        f"400張以上大戶: {b400_pct:.2f}%（{b400_people:,} 人）| "
        f"10張以下散戶: {small_pct:.2f}%（{small_people:,} 人）"
    )
    return "\n".join(lines)


def week_metrics(week: WeekDistribution) -> Metrics:
    """Holder counts and ratios of the groups people watch: 千張大戶, 400張以上, 10張以下."""
    big_people, big_pct = _group(week.levels, BIG_HOLDER_LEVELS)
    b400_people, b400_pct = _group(week.levels, BIG_HOLDER_400_LEVELS)
    small_people, small_pct = _group(week.levels, SMALL_HOLDER_LEVELS)
    return {
        "total_people": week.total.people,
        "big_people": big_people, "big_pct": big_pct,
        "b400_people": b400_people, "b400_pct": b400_pct,
        "small_people": small_people, "small_pct": small_pct,
    }


def format_trend(code: str, weekly: List[Tuple[str, Metrics]], queried: List[str]) -> str:
    """Newest-first trend lines with the change against the previous (older) week shown.

    ``queried`` is every week asked for, newest first. When a week in between had no data the
    comparison is against an older week, and the label names that week instead of 較前週.
    """
    lines = [f"【{code} 集保股權分散週趨勢】（共 {len(weekly)} 週，由新到舊；pp＝百分點）\n"]
    for i, (date, m) in enumerate(weekly):
        line = (
            f"{date[:4]}-{date[4:6]}-{date[6:]} | 總人數 {m['total_people']:,} | "
            f"千張大戶 {m['big_pct']:.2f}%（{m['big_people']:,} 人）| "
            f"400張以上 {m['b400_pct']:.2f}%（{m['b400_people']:,} 人）| "
            f"10張以下 {m['small_pct']:.2f}%（{m['small_people']:,} 人）"
        )
        if i + 1 < len(weekly):
            prev_date, prev = weekly[i + 1]
            adjacent = queried.index(prev_date) == queried.index(date) + 1
            label = "較前週" if adjacent else f"較 {prev_date[4:6]}-{prev_date[6:]}"
            line += (
                f" | {label}: 千張大戶 {m['big_pct'] - prev['big_pct']:+.2f}pp（{m['big_people'] - prev['big_people']:+,} 人）、"
                f"400張以上 {m['b400_pct'] - prev['b400_pct']:+.2f}pp、"
                f"10張以下 {m['small_pct'] - prev['small_pct']:+.2f}pp（{m['small_people'] - prev['small_people']:+,} 人）"
            )
        lines.append(line)
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TDCC shareholding distribution tools."""
    _client = client or TWSEAPIClient.get_instance()
    # Past weeks never change, so keep them for the life of the process (bounded).
    # Tools run in worker threads, so eviction + insert happen under a lock.
    week_cache: Dict[Tuple[str, str], WeekDistribution] = {}
    week_cache_lock = threading.Lock()

    def _latest_week_table(code: str) -> str:
        dist = latest_distribution(_client, code)
        if dist is None:
            return f"查無證券代號 {code} 的集保股權分散資料"
        header = f"【{code} 集保戶股權分散表】資料日期: {dist.date.isoformat()}\n"
        return header + summarize(dist.levels)

    @time_budget(TREND_BUDGET, "已查到的週次會留在快取，可稍後再試或減少 weeks")
    def _weekly_trend(code: str, weeks: int) -> str:
        query = StockQuery(_client)
        weekly: List[Tuple[str, Metrics]] = []
        for date in query.dates[:weeks]:
            week = week_cache.get((code, date))
            if week is None:
                week = query.week(code, date)
                if week is None:  # 查無此資料
                    if not weekly:
                        return f"查無證券代號 {code} 的集保股權分散資料"
                    continue  # no data for that week
                with week_cache_lock:
                    if len(week_cache) >= MAX_CACHED_WEEKS:
                        week_cache.pop(next(iter(week_cache)))
                    week_cache[(code, date)] = week
            weekly.append((date, week_metrics(week)))
        if not weekly:
            return f"查無證券代號 {code} 的集保股權分散資料"
        return format_trend(code, weekly, query.dates[:weeks])

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_shareholding_distribution(code: str, weeks: Annotated[int, Field(ge=1, le=MAX_WEEKS)] = 1) -> str:
        """查詢個股「集保戶股權分散表」，觀察籌碼集中度：預設最新一週的完整級距表；
        weeks > 1 時改為逐週趨勢（最多 13 週）：每週的總人數、千張大戶／400張以上／10張以下散戶的
        持股比例與人數，以及較前一週的增減，可看出大戶是在增持還是減持。
        資料來自臺灣集中保管結算所，每週更新（通常週五／週六公布前一個交易週的資料），
        上市、上櫃、興櫃、ETF 皆可查。

        回傳：weeks=1：資料日期、17 個持股分級的人數／股數／占比，以及大戶／散戶摘要；
        weeks>1：由新到舊每週的大戶與散戶持股比例、人數與週變化

        Args:
            code: 證券代號，例如 "2330"、"0050"
            weeks: 週數（預設 1＝最新一週的完整 17 級距表；2～13＝逐週趨勢，每多一週多一次查詢，較慢）
        """
        code = code.strip()
        return _latest_week_table(code) if weeks == 1 else _weekly_trend(code, weeks)
