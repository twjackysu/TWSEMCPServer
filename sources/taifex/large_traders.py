"""largeTraderFutDown / largeTraderOptDown: 期貨 / 選擇權大額交易人未沖銷部位 — top 5 / top 10 traders' positions.

``POST https://www.taifex.com.tw/cht/3/largeTraderFutDown`` with the date range (no contract filter: any
other field is ignored, every commodity comes back). Reply (cp950 CSV)::

    日期,商品(契約),商品名稱(契約名稱),到期月份(週別),交易人類別,前五大交易人買方,前五大交易人賣方,
    前十大交易人買方,前十大交易人賣方,全市場未沖銷部位數
    2025/01/03,TX     ,臺股期貨(TX+MTX/4+TMF/20)           ,999999  ,0,28962,34725,38873,48543,85490

largeTraderOptDown adds 買賣權 (買權 / 賣權) after the name and rejects a span of a year. 商品(契約) and
到期月份 are padded with spaces (some names too); 交易人類別 0 = 所有交易人, 1 = 特定法人; 到期月份 999999 is
every month together. Columns are found by name; same layout checked 2005–2026.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from utils.api_client import TWSEAPIClient
from utils.taifex import TAIFEX_DOWNLOAD_BASE

from .download import count, download_table, trade_date

LARGE_TRADER_FUT_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/largeTraderFutDown"
LARGE_TRADER_OPT_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/largeTraderOptDown"
FIELDS = ("日期", "商品(契約)", "商品名稱(契約名稱)", "到期月份(週別)", "交易人類別", "前五大交易人買方",
          "前五大交易人賣方", "前十大交易人買方", "前十大交易人賣方", "全市場未沖銷部位數")


@dataclass(frozen=True)
class LargeTraderPosition:
    day: date
    contract: str              # 商品(契約): TX, TXO, CDF …
    name: str                  # 商品名稱(契約名稱): 臺股期貨(TX+MTX/4+TMF/20), 臺指 …
    month: str                 # 到期月份(週別): 202611, 202611W1, 999999 (all months), 666666
    trader_type: str           # 交易人類別 as published: "0" 所有交易人, "1" 特定法人
    top5_buy: Optional[int]    # 前五大交易人買方 (contracts)
    top5_sell: Optional[int]
    top10_buy: Optional[int]
    top10_sell: Optional[int]
    market_oi: Optional[int]   # 全市場未沖銷部位數
    call_put: str = ""         # 買賣權 (options only): 買權 / 賣權


def _positions(client: TWSEAPIClient, url: str, source: str, start: date, end: date,
               options: bool) -> Optional[List[LargeTraderPosition]]:
    table = download_table(client, url, source, FIELDS + (("買賣權",) if options else ()), start, end)
    if table is None:
        return None
    col, rows = table
    return [LargeTraderPosition(
        day=trade_date(r[col["日期"]], source),
        contract=r[col["商品(契約)"]].strip(),
        name=r[col["商品名稱(契約名稱)"]].strip(),
        month=r[col["到期月份(週別)"]].strip(),
        trader_type=r[col["交易人類別"]].strip(),
        top5_buy=count(r[col["前五大交易人買方"]]),
        top5_sell=count(r[col["前五大交易人賣方"]]),
        top10_buy=count(r[col["前十大交易人買方"]]),
        top10_sell=count(r[col["前十大交易人賣方"]]),
        market_oi=count(r[col["全市場未沖銷部位數"]]),
        call_put=r[col["買賣權"]].strip() if options else "",
    ) for r in rows]


def futures_large_traders(client: TWSEAPIClient, start: date, end: date) -> Optional[List[LargeTraderPosition]]:
    """Every futures commodity's large-trader positions from ``start`` to ``end``, or None when TAIFEX has none."""
    return _positions(client, LARGE_TRADER_FUT_DOWN_URL, "largeTraderFutDown", start, end, False)


def option_large_traders(client: TWSEAPIClient, start: date, end: date) -> Optional[List[LargeTraderPosition]]:
    """Every option commodity's large-trader positions from ``start`` to ``end``, or None when TAIFEX has none."""
    return _positions(client, LARGE_TRADER_OPT_DOWN_URL, "largeTraderOptDown", start, end, True)
