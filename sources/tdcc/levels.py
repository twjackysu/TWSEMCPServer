"""One row of 集保戶股權分散表 — the record both TDCC sources return (the open-data CSV and the query page).

持股分級 1–15 are holding-size brackets in shares (1: 1–999 股 … 15: over 1,000,000 股), 16 is 差異數調整
(reconciliation with the share register) and 17 the total. The two sources agree on 1–15 and the total (compared
2026-10-02 for 2330, 6488, 0050); 差異數調整 differs: the query page keeps its sign and leaves the row out when it is
zero, the CSV prints its absolute value.
"""

from dataclasses import dataclass
from decimal import Decimal

ADJUSTMENT = 16  # 差異數調整
TOTAL = 17       # 合計


@dataclass(frozen=True)
class LevelHolding:
    level: int    # 持股分級 1–17
    people: int   # 人數
    shares: int   # 股數 (單位數 for ETFs)
    pct: Decimal  # 占集保庫存數比例 (%), the published digits ("84.78")
