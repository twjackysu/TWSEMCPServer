"""TAIFEX futures / options daily market report (每日行情), latest day or any past period.

Source: www.taifex.com.tw download pages futDataDown / optDataDown. These replace the
openapi DailyMarketReportFut / DailyMarketReportOpt tools and the former *_daily_history
tools. On 2026-09-29 the download pages carried every openapi row with the same values,
plus calendar-spread rows for futures and real best-bid/ask and historical high/low for
~2,000 option rows that openapi left as "-". ``commodity_id="all"`` returns every contract,
which is how available contract codes are listed.
"""

from collections import defaultdict
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

FUT_DATA_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/futDataDown"
OPT_DATA_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/optDataDown"
ALL_CONTRACTS = "all"
# Server-enforced ~1 month per request.
MAX_SPAN_DAYS = 31
# Ceiling on rows written to a response: a month of TX alone is ~500 rows, and a single
# option contract month is ~23,000 rows over a month.
MAX_OUTPUT_ROWS = 300


def has_regular_session(parsed) -> bool:
    """A day counts as the latest trading day only once its 一般 (regular) session is in.

    During the regular session the download pages already list today's date with just
    the overnight 盤後 rows, which would pass for a whole day. Column 17 is 交易時段.
    """
    return any(len(r) > 17 and r[17].strip() == "一般" for r in parsed[1])


def _is_zero(value: str) -> bool:
    return value.strip() in ("", "0", "-")


def _to_int(value: str) -> int:
    try:
        return int(value.replace(",", "").strip())
    except ValueError:
        return 0


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _download(url: str, contract: str):
        def fetch(start_dt, end_dt):
            body = _client.fetch_bytes(
                url,
                method="POST",
                headers=TAIFEX_HEADERS,
                data=download_form(start_dt, end_dt, down_type="1", commodity_id=contract, commodity_id2=""),
                cache_ttl=TAIFEX_CACHE_TTL,
            )
            return decode_and_parse_csv(body)
        return fetch

    def _list_contracts(url: str, kind: str, start_date: str, end_date: str) -> str:
        parsed, label, error = fetch_period(_download(url, ALL_CONTRACTS), start_date, end_date, MAX_SPAN_DAYS, "20260601", is_complete=has_regular_session)
        if error:
            return error
        if parsed is None:
            return f"查無 {label} 的{kind}行情資料"
        contracts = sorted({r[1].strip() for r in parsed[1]})
        return f"{label} 可用{kind}契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

    @mcp.tool
    @handle_api_errors()
    def get_daily_futures_market_report(contract: str = "TX", start_date: str = "", end_date: str = "") -> str:
        """查詢期貨每日交易行情（開高低收、漲跌、成交量、結算價、未平倉量、最後最佳買賣價）：
        預設最新交易日，也可指定任意過去區間（最長一個月，資料可回溯至 2020 年以前）。
        常用契約代碼：TX（臺股期貨）、MTX（小型臺指）、TE（電子期貨）、TF（金融期貨）。

        Args:
            contract: 期貨契約代碼，預設 TX。留空則列出所有可用契約代碼
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月

        Returns:
            每個交易日、每個到期月份、一般與盤後時段的行情；價差組合只列出有成交的
        """
        contract = contract.strip().upper()
        if not contract:
            return _list_contracts(FUT_DATA_DOWN_URL, "期貨", start_date, end_date)

        parsed, label, error = fetch_period(_download(FUT_DATA_DOWN_URL, contract), start_date, end_date, MAX_SPAN_DAYS, "20260601", is_complete=has_regular_session)
        if error:
            return error
        if parsed is None:
            return f"查無契約 {contract} 在 {label} 的行情資料，請確認契約代碼（留空 contract 可列出可用代碼）"

        # r: 交易日期,契約,到期月份(週別),開盤價,最高價,最低價,收盤價,漲跌價,漲跌%,成交量,結算價,
        #    未沖銷契約數,最後最佳買價,最後最佳賣價,歷史最高價,歷史最低價,是否因訊息面暫停交易,交易時段,...
        # 價差組合（到期月份含 "/"）多半整天無成交，只保留有成交的
        rows = [r for r in parsed[1] if "/" not in r[2] or not _is_zero(r[9])]
        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【期貨每日交易行情】{contract} | {label}（共 {total} 筆{cap_note}）\n"]
        for r in shown:
            date, month, session = r[0], r[2].strip(), r[17]
            o, h, l, c, change, pct = r[3], r[4], r[5], r[6], r[7], r[8]
            vol, settle, oi, bid, ask = r[9], r[10], r[11], r[12], r[13]
            lines.append(
                f"{date} | {month} | {session} | 開:{o} 高:{h} 低:{l} 收:{c} | 漲跌:{change}({pct}) | "
                f"量:{vol} | 結算:{settle} | 未平倉:{oi} | 最佳買/賣:{bid}/{ask}"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_daily_options_market_report(contract: str = "TXO", start_date: str = "", end_date: str = "",
                                        contract_month: str = "", call_put: str = "", limit: int = 30) -> str:
        """查詢選擇權每日交易行情：預設最新交易日，也可指定任意過去區間（最長一個月）。
        未指定 contract_month 時，每個交易日只列有成交的履約價，依成交量由大到小取前 limit 筆，並附上可用到期月份；
        指定 contract_month 時列出該到期月份的完整履約價序列。
        常用契約代碼：TXO（臺指選擇權）、TEO（電子選擇權）、TFO（金融選擇權）。

        Args:
            contract: 選擇權契約代碼，預設 TXO。留空則列出所有可用契約代碼
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月
            contract_month: 到期月份/週次，例如「202610」或「202610W1」（選填）
            call_put: 篩選「買權」或「賣權」，留空則顯示全部
            limit: 未指定 contract_month 時，每個交易日顯示的筆數（依成交量排序，預設 30）

        Returns:
            履約價、買賣權、開高低收、成交量、結算價、未平倉量、最後最佳買賣價
        """
        contract = contract.strip().upper()
        if not contract:
            return _list_contracts(OPT_DATA_DOWN_URL, "選擇權", start_date, end_date)

        parsed, label, error = fetch_period(_download(OPT_DATA_DOWN_URL, contract), start_date, end_date, MAX_SPAN_DAYS, "20260601", is_complete=has_regular_session)
        if error:
            return error
        if parsed is None:
            return f"查無契約 {contract} 在 {label} 的選擇權行情資料，請確認契約代碼（留空 contract 可列出可用代碼）"

        # r: 交易日期,契約,到期月份(週別),履約價,買賣權,開盤價,最高價,最低價,收盤價,成交量,結算價,
        #    未沖銷契約數,最後最佳買價,最後最佳賣價,歷史最高價,歷史最低價,是否因訊息面暫停交易,交易時段,漲跌價,漲跌%,...
        rows = parsed[1]
        months = sorted({r[2].strip() for r in rows})
        if call_put:
            rows = [r for r in rows if r[4] == call_put]
        if contract_month:
            rows = [r for r in rows if r[2].strip() == contract_month]
            if not rows:
                return f"查無 {contract} 到期月份 {contract_month} 在 {label} 的資料。可用到期月份：{'、'.join(months)}"

        if contract_month:
            total = len(rows)
            shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date，或加上 call_put")
            header = f"【選擇權每日交易行情】{contract} {contract_month} | {label}（共 {total} 筆{cap_note}）\n"
        else:
            by_date = defaultdict(list)
            for r in rows:
                if not _is_zero(r[9]):
                    by_date[r[0]].append(r)
            shown = []
            for date in sorted(by_date):
                shown += sorted(by_date[date], key=lambda r: -_to_int(r[9]))[:limit]
            total = sum(len(v) for v in by_date.values())
            header = (
                f"【選擇權每日交易行情】{contract} | {label}（有成交共 {total} 筆，每日依成交量取前 {limit} 筆）\n"
                f"可用到期月份：{'、'.join(months)}（指定 contract_month 可查完整履約價序列）\n"
            )

        lines = [header]
        for r in shown:
            date, month, strike, cp, session = r[0], r[2].strip(), r[3], r[4], r[17]
            o, h, l, c, vol, settle, oi, bid, ask = r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13]
            lines.append(
                f"{date} | {month} {cp} 履約:{strike} | {session} | 開:{o} 高:{h} 低:{l} 收:{c} | "
                f"量:{vol} | 結算:{settle} | 未平倉:{oi} | 最佳買/賣:{bid}/{ask}"
            )
        return "\n".join(lines)
