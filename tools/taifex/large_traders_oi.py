"""TAIFEX large traders (大額交易人) open interest, futures and options, latest day or any period.

Both come from www.taifex.com.tw download pages (largeTraderFutDown / largeTraderOptDown,
``sources.taifex.large_traders``). They replace the openapi OpenInterestOfLargeTradersFutures / ...Options
tools (the futures one had been serving CSV instead of JSON since 2026-07). On 2026-09-29 all 1,386 futures
rows, and on 2026-10-07 all 320 options rows, matched the openapi data value for value; the only difference
is that the all-months total is coded 999999 on the download pages instead of openapi's 999912.
Neither page has a contract filter (any extra field is ignored), so every request returns all
commodities (~340 futures, ~36 options) and filtering is local.
"""

from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.taifex.large_traders import LargeTraderPosition, futures_large_traders, option_large_traders
from utils import TWSEAPIClient, cap_rows, plain
from toolkit import TradingDate, handle_api_errors
from utils.taifex import fetch_period

# The payload doesn't shrink with a contract filter (~1,100 futures rows per day), and a full
# year is rejected by the options page, so keep spans short.
MAX_SPAN_DAYS = 31
MAX_OUTPUT_ROWS = 300

_TYPE_LABELS = {"0": "所有交易人", "1": "特定法人"}
# 999912 (openapi) and 999999 (download pages) are the same all-months total.
_SETTLE_LABELS = {"666666": "所有月份合計", "999912": "所有月份總計", "999999": "所有月份總計"}


def month_label(code: str) -> str:
    code = code.strip()
    return _SETTLE_LABELS.get(code, f"到期月 {code}")


def _positions(r: LargeTraderPosition) -> str:
    return (f"{month_label(r.month)} | {_TYPE_LABELS.get(r.trader_type, r.trader_type)} | "
            f"前五大: 多 {plain(r.top5_buy)} / 空 {plain(r.top5_sell)} | "
            f"前十大: 多 {plain(r.top10_buy)} / 空 {plain(r.top10_sell)} | 市場總未平倉: {plain(r.market_oi)}")


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_futures_oi(contract: str = "TX", start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢期貨大額交易人（前五大、前十大）未沖銷部位，觀察大戶持倉方向：預設最新交易日，
        也可回溯任意區間（最長一個月）。前五大、前十大部位集中度越高，代表市場籌碼越集中。
        常用契約：TX（臺股期貨，含 MTX 折算）、MTX、TE、TF。

        回傳：每個交易日、每個到期月份的前五大／前十大交易人多空部位及全市場未沖銷部位，區分所有交易人與特定法人

        Args:
            contract: 期貨契約代碼，預設 TX。留空則列出所有可用契約代碼
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月
        """
        rows, label, error = fetch_period(lambda s, e: futures_large_traders(_client, s, e),
                                          start_date, end_date, MAX_SPAN_DAYS)
        if error:
            raise ToolError(error)
        if rows is None:
            return f"查無 {label} 的期貨大額交易人未沖銷部位資料"

        contract = contract.strip().upper()
        if not contract:
            contracts = sorted({(r.contract, r.name) for r in rows})
            return f"{label} 可用期貨契約代碼（共 {len(contracts)} 種）：\n" + "、".join(f"{c}({n})" for c, n in contracts)

        rows = [r for r in rows if r.contract == contract]
        if not rows:
            return f"查無契約 {contract} 在 {label} 的大額交易人資料（留空 contract 可列出可用代碼）"

        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【期貨大額交易人未沖銷部位】{contract}（{rows[0].name}）| {label}（共 {total} 筆{cap_note}）\n"]
        lines += [f"{r.day:%Y/%m/%d} | {_positions(r)}" for r in shown]
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_options_oi(contract: str = "TXO", call_put: str = "",
                                     start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢選擇權大額交易人（前五大、前十大）未沖銷部位，觀察大戶選擇權布局：預設最新交易日，
        也可回溯任意區間（最長一個月）。常用契約：TXO（臺指選擇權）。

        回傳：每個交易日、每個到期月份的前五大／前十大交易人買賣權部位及全市場未沖銷部位，區分所有交易人與特定法人

        Args:
            contract: 選擇權契約代碼，預設 TXO。留空則列出所有可用契約代碼
            call_put: 篩選「買權」或「賣權」，留空則顯示全部
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月
        """
        rows, label, error = fetch_period(lambda s, e: option_large_traders(_client, s, e),
                                          start_date, end_date, MAX_SPAN_DAYS)
        if error:
            raise ToolError(error)
        if rows is None:
            return f"查無 {label} 的選擇權大額交易人未沖銷部位資料"

        contract = contract.strip().upper()
        if not contract:
            contracts = sorted({(r.contract, r.name) for r in rows})
            return f"{label} 可用選擇權契約代碼（共 {len(contracts)} 種）：\n" + "、".join(f"{c}({n})" for c, n in contracts)

        rows = [r for r in rows if r.contract == contract]
        if not rows:
            return f"查無契約 {contract} 在 {label} 的大額交易人資料（留空 contract 可列出可用代碼）"
        if call_put in ("買權", "賣權"):
            rows = [r for r in rows if r.call_put == call_put]
            if not rows:
                return f"查無契約 {contract} 在 {label} 的{call_put}大額交易人資料"

        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date，或加上 call_put")
        lines = [f"【選擇權大額交易人未沖銷部位】{contract}（{rows[0].name}）| {label}（共 {total} 筆{cap_note}）\n"]
        lines += [f"{r.day:%Y/%m/%d} | {r.call_put} | {_positions(r)}" for r in shown]
        return "\n".join(lines)
