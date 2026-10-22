"""TAIFEX futures / options daily market report (每日行情), latest day or any past period.

Source: www.taifex.com.tw download pages futDataDown / optDataDown, read through
sources/taifex/daily_report.py. These replace the openapi DailyMarketReportFut /
DailyMarketReportOpt tools and the former *_daily_history tools. On 2026-09-29 the download pages
carried every openapi row with the same values, plus calendar-spread rows for futures and real
best-bid/ask and historical high/low for ~2,000 option rows that openapi left as "-".
``commodity_id="all"`` returns every contract, which is how available contract codes are listed.
"""

from collections import defaultdict
from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient, cap_rows, plain
from toolkit import Limit, TradingDate, handle_api_errors
from utils.taifex import fetch_period, is_stock_code, stock_futures_contracts
from sources.taifex.daily_report import ALL_CONTRACTS, futures_quotes, has_regular_session, option_quotes

# Server-enforced ~1 month per request.
MAX_SPAN_DAYS = 31
# Ceiling on rows written to a response: a month of TX alone is ~500 rows, and a single
# option contract month is ~23,000 rows over a month.
MAX_OUTPUT_ROWS = 300


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _fetch(gateway, contract: str):
        return lambda start_dt, end_dt: gateway(_client, contract, start_dt, end_dt)

    def _list_contracts(gateway, kind: str, start_date: str, end_date: str) -> str:
        quotes, label, error = fetch_period(_fetch(gateway, ALL_CONTRACTS), start_date, end_date, MAX_SPAN_DAYS,
                                            is_complete=has_regular_session)
        if error:
            raise ToolError(error)
        if quotes is None:
            return f"查無 {label} 的{kind}行情資料"
        contracts = sorted({q.contract for q in quotes})
        return f"{label} 可用{kind}契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

    @mcp.tool
    @handle_api_errors()
    def get_daily_futures_market_report(contract: str = "TX", start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢期貨每日交易行情（開高低收、漲跌、成交量、結算價、未平倉量、最後最佳買賣價）：
        預設最新交易日，也可指定任意過去區間（最長一個月，資料可回溯至 2020 年以前）。
        常用契約代碼：TX（臺股期貨，俗稱台指期）、MTX（小型臺指）、TE（電子期貨）、TF（金融期貨）。
        也可直接填股票／ETF 代號（例如 "2330"、"0050"），會列出該標的所有股票期貨契約
        （標準型與小型，例如台積電 CDF、QFF）。

        回傳：每個交易日、每個到期月份、一般與盤後時段的行情；價差組合只列出有成交的

        Args:
            contract: 期貨契約代碼，預設 TX；或股票／ETF 代號。留空則列出所有可用契約代碼
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月
        """
        contract = contract.strip().upper()
        if not contract:
            return _list_contracts(futures_quotes, "期貨", start_date, end_date)

        title, contracts = contract, [contract]
        if is_stock_code(contract):
            matches = stock_futures_contracts(_client, contract)
            if not matches:
                return f"{contract} 沒有股票期貨（股票期貨標的清單中查無此代號）"
            contracts = [c for c, _name in matches]
            title = f"{contract} {matches[0][1]} 股票期貨（{'、'.join(contracts)}）"

        all_quotes, label = [], ""
        for code in contracts:
            quotes, label, error = fetch_period(_fetch(futures_quotes, code), start_date, end_date, MAX_SPAN_DAYS,
                                                is_complete=has_regular_session)
            if error:
                raise ToolError(error)
            if quotes is not None:
                all_quotes.extend(quotes)
        if not all_quotes:
            return f"查無契約 {contract} 在 {label} 的行情資料，請確認契約代碼（留空 contract 可列出可用代碼）"

        # 價差組合（到期月份含 "/"）多半整天無成交，只保留有成交的
        quotes = [q for q in all_quotes if "/" not in q.month or q.volume]
        total = len(quotes)
        shown, cap_note = cap_rows(quotes, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date")
        lines = [f"【期貨每日交易行情】{title} | {label}（共 {total} 筆{cap_note}）\n"]
        for q in shown:
            month = f"{q.contract} {q.month}" if len(contracts) > 1 else q.month
            lines.append(
                f"{q.day:%Y/%m/%d} | {month} | {q.session} | 開:{plain(q.open)} 高:{plain(q.high)} 低:{plain(q.low)} "
                f"收:{plain(q.close)} | 漲跌:{plain(q.change)}({q.change_pct}) | 量:{plain(q.volume)} | "
                f"結算:{plain(q.settlement)} | 未平倉:{plain(q.open_interest)} | "
                f"最佳買/賣:{plain(q.best_bid)}/{plain(q.best_ask)}"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_daily_options_market_report(contract: str = "TXO", start_date: TradingDate = "", end_date: TradingDate = "",
                                        contract_month: str = "", call_put: str = "", limit: Limit = 30) -> str:
        """查詢選擇權每日交易行情：預設最新交易日，也可指定任意過去區間（最長一個月）。
        未指定 contract_month 時，每個交易日只列有成交的履約價，依成交量由大到小取前 limit 筆，並附上可用到期月份；
        指定 contract_month 時列出該到期月份的完整履約價序列。
        常用契約代碼：TXO（臺指選擇權）、TEO（電子選擇權）、TFO（金融選擇權）。

        回傳：履約價、買賣權、開高低收、成交量、結算價、未平倉量、最後最佳買賣價

        Args:
            contract: 選擇權契約代碼，預設 TXO。留空則列出所有可用契約代碼
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過一個月
            contract_month: 到期月份/週次，例如「202610」或「202610W1」（選填）
            call_put: 篩選「買權」或「賣權」，留空則顯示全部
            limit: 未指定 contract_month 時，每個交易日顯示的筆數（依成交量排序，預設 30）
        """
        contract = contract.strip().upper()
        if not contract:
            return _list_contracts(option_quotes, "選擇權", start_date, end_date)

        quotes, label, error = fetch_period(_fetch(option_quotes, contract), start_date, end_date, MAX_SPAN_DAYS,
                                            is_complete=has_regular_session)
        if error:
            raise ToolError(error)
        if quotes is None:
            return f"查無契約 {contract} 在 {label} 的選擇權行情資料，請確認契約代碼（留空 contract 可列出可用代碼）"

        months = sorted({q.month for q in quotes})
        if call_put:
            quotes = [q for q in quotes if q.call_put == call_put]
        if contract_month:
            quotes = [q for q in quotes if q.month == contract_month]
            if not quotes:
                return f"查無 {contract} 到期月份 {contract_month} 在 {label} 的資料。可用到期月份：{'、'.join(months)}"

        if contract_month:
            total = len(quotes)
            shown, cap_note = cap_rows(quotes, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date，或加上 call_put")
            header = f"【選擇權每日交易行情】{contract} {contract_month} | {label}（共 {total} 筆{cap_note}）\n"
        else:
            by_date = defaultdict(list)
            for q in quotes:
                if q.volume:
                    by_date[q.day].append(q)
            shown = []
            for day in sorted(by_date):
                shown += sorted(by_date[day], key=lambda q: -(q.volume or 0))[:limit]
            total = sum(len(v) for v in by_date.values())
            header = (
                f"【選擇權每日交易行情】{contract} | {label}（有成交共 {total} 筆，每日依成交量取前 {limit} 筆）\n"
                f"可用到期月份：{'、'.join(months)}（指定 contract_month 可查完整履約價序列）\n"
            )

        lines = [header]
        for q in shown:
            lines.append(
                f"{q.day:%Y/%m/%d} | {q.month} {q.call_put} 履約:{plain(q.strike)} | {q.session} | 開:{plain(q.open)} "
                f"高:{plain(q.high)} 低:{plain(q.low)} 收:{plain(q.close)} | 量:{plain(q.volume)} | "
                f"結算:{plain(q.settlement)} | 未平倉:{plain(q.open_interest)} | "
                f"最佳買/賣:{plain(q.best_bid)}/{plain(q.best_ask)}"
            )
        return "\n".join(lines)
