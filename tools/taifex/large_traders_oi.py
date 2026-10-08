"""TAIFEX large traders (大額交易人) open interest, futures and options, latest day or any period.

Both come from www.taifex.com.tw download pages (largeTraderFutDown / largeTraderOptDown).
They replace the openapi OpenInterestOfLargeTradersFutures / ...Options tools (the futures one
had been serving CSV instead of JSON since 2026-07). On 2026-09-29 all 1,386 futures rows, and on
2026-10-07 all 320 options rows, matched the openapi data value for value; the only difference
is that the all-months total is coded 999999 on the download pages instead of openapi's 999912.
Neither page has a contract filter (any extra field is ignored), so every request returns all
commodities (~340 futures, ~36 options) and filtering is local.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, cap_rows
from utils.taifex import (
    TAIFEX_CACHE_TTL,
    TAIFEX_DOWNLOAD_BASE,
    TAIFEX_HEADERS,
    decode_and_parse_csv,
    download_form,
    fetch_period,
)

LARGE_TRADER_FUT_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/largeTraderFutDown"
LARGE_TRADER_OPT_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/largeTraderOptDown"
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


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _fetcher(url: str):
        def fetch(start_dt, end_dt):
            body = _client.fetch_bytes(
                url,
                method="POST",
                headers=TAIFEX_HEADERS,
                data=download_form(start_dt, end_dt),
                cache_ttl=TAIFEX_CACHE_TTL,
            )
            return decode_and_parse_csv(body)
        return fetch

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_futures_oi(contract: str = "TX", start_date: str = "", end_date: str = "") -> str:
        """查詢期貨大額交易人（前五大、前十大）未沖銷部位，觀察大戶持倉方向：預設最新交易日，
        也可回溯任意區間（最長一個月）。前五大、前十大部位集中度越高，代表市場籌碼越集中。
        常用契約：TX（臺股期貨，含 MTX 折算）、MTX、TE、TF。

        Args:
            contract: 期貨契約代碼，預設 TX。留空則列出所有可用契約代碼
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月

        Returns:
            每個交易日、每個到期月份的前五大／前十大交易人多空部位及全市場未沖銷部位，區分所有交易人與特定法人
        """
        parsed, label, error = fetch_period(
            _fetcher(LARGE_TRADER_FUT_DOWN_URL), start_date, end_date, MAX_SPAN_DAYS, "20260601"
        )
        if error:
            return error
        if parsed is None:
            return f"查無 {label} 的期貨大額交易人未沖銷部位資料"
        rows = parsed[1]

        contract = contract.strip().upper()
        if not contract:
            contracts = sorted({(r[1].strip(), r[2].strip()) for r in rows})
            return f"{label} 可用期貨契約代碼（共 {len(contracts)} 種）：\n" + "、".join(f"{c}({n})" for c, n in contracts)

        # r: 日期,商品(契約),商品名稱(契約名稱),到期月份(週別),交易人類別,前五大買方,前五大賣方,
        #    前十大買方,前十大賣方,全市場未沖銷部位數
        rows = [r for r in rows if r[1].strip() == contract]
        if not rows:
            return f"查無契約 {contract} 在 {label} 的大額交易人資料（留空 contract 可列出可用代碼）"

        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【期貨大額交易人未沖銷部位】{contract}（{rows[0][2].strip()}）| {label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            lines.append(
                f"{r[0]} | {month_label(r[3])} | {_TYPE_LABELS.get(r[4].strip(), r[4])} | "
                f"前五大: 多 {r[5]} / 空 {r[6]} | 前十大: 多 {r[7]} / 空 {r[8]} | 市場總未平倉: {r[9]}"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_options_oi(contract: str = "TXO", call_put: str = "",
                                     start_date: str = "", end_date: str = "") -> str:
        """查詢選擇權大額交易人（前五大、前十大）未沖銷部位，觀察大戶選擇權布局：預設最新交易日，
        也可回溯任意區間（最長一個月）。常用契約：TXO（臺指選擇權）。

        Args:
            contract: 選擇權契約代碼，預設 TXO。留空則列出所有可用契約代碼
            call_put: 篩選「買權」或「賣權」，留空則顯示全部
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月

        Returns:
            每個交易日、每個到期月份的前五大／前十大交易人買賣權部位及全市場未沖銷部位，區分所有交易人與特定法人
        """
        parsed, label, error = fetch_period(
            _fetcher(LARGE_TRADER_OPT_DOWN_URL), start_date, end_date, MAX_SPAN_DAYS, "20260601"
        )
        if error:
            return error
        if parsed is None:
            return f"查無 {label} 的選擇權大額交易人未沖銷部位資料"
        rows = parsed[1]

        contract = contract.strip().upper()
        if not contract:
            contracts = sorted({(r[1].strip(), r[2].strip()) for r in rows})
            return f"{label} 可用選擇權契約代碼（共 {len(contracts)} 種）：\n" + "、".join(f"{c}({n})" for c, n in contracts)

        # r: 日期,商品(契約),商品名稱(契約名稱),買賣權,到期月份(週別),交易人類別,前五大買方,前五大賣方,
        #    前十大買方,前十大賣方,全市場未沖銷部位數
        rows = [r for r in rows if r[1].strip() == contract]
        if not rows:
            return f"查無契約 {contract} 在 {label} 的大額交易人資料（留空 contract 可列出可用代碼）"
        if call_put in ("買權", "賣權"):
            rows = [r for r in rows if r[3].strip() == call_put]
            if not rows:
                return f"查無契約 {contract} 在 {label} 的{call_put}大額交易人資料"

        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date，或加上 call_put")
        lines = [f"【選擇權大額交易人未沖銷部位】{contract}（{rows[0][2].strip()}）| {label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            lines.append(
                f"{r[0]} | {r[3].strip()} | {month_label(r[4])} | {_TYPE_LABELS.get(r[5].strip(), r[5])} | "
                f"前五大: 多 {r[6]} / 空 {r[7]} | 前十大: 多 {r[8]} / 空 {r[9]} | 市場總未平倉: {r[10]}"
            )
        return "\n".join(lines)
