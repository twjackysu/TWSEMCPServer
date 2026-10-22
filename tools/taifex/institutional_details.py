"""TAIFEX 三大法人 by contract (futures / options) and options by call-put, latest day or any period.

Source: www.taifex.com.tw download pages futContractsDateDown / optContractsDateDown /
callsAndPutsDateDown (``sources.taifex.institutional``). These replace the openapi
...DetailsOfFuturesContracts / ...DetailsOfOptionsContracts / ...DetailsOfCallsAndPuts tools and the three
former *_history tools. On 2026-09-29 every openapi row matched these endpoints value for value,
and the futures page additionally carried 臺灣中型100期貨, which openapi omitted.
"""

from collections import OrderedDict
from typing import List, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.taifex.institutional import (
    ContractPositions,
    calls_puts_positions,
    futures_contract_positions,
    option_contract_positions,
)
from utils import TWSEAPIClient, cap_rows, plain
from toolkit import TradingDate, handle_api_errors
from utils.taifex import fetch_period, is_contract_code

# No server-enforced span cap observed (3-month pulls work); retention runs out ~3 years back.
MAX_SPAN_DAYS = 92
# Unfiltered futures are ~69 rows per day, so a 92-day span is ~6,000 rows.
MAX_OUTPUT_ROWS = 300


def format_trader_rows(rows: List[ContractPositions], value_unit: str, side_labels=("多", "空")) -> List[str]:
    """Render ``ContractPositions`` grouped by date and contract (and CALL / PUT on the calls/puts page)."""
    long_, short_ = side_labels
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for r in rows:
        key = (f"{r.day:%Y/%m/%d}", r.contract) + ((r.call_put,) if r.call_put else ())
        groups.setdefault(key, []).append(r)
    lines = []
    for key, items in groups.items():
        lines.append(f"▶ {' '.join(key)}")
        for r in items:
            p = r.positions
            lines.append(
                f"  {r.identity}\n"
                f"    交易量: {long_} {plain(p.long_volume)} / {short_} {plain(p.short_volume)} / 淨 {plain(p.net_volume)}\n"
                f"    交易金額({value_unit}): {long_} {plain(p.long_value)} / {short_} {plain(p.short_value)} / "
                f"淨 {plain(p.net_value)}\n"
                f"    未平倉口數: {long_} {plain(p.long_oi)} / {short_} {plain(p.short_oi)} / 淨 {plain(p.net_oi)}\n"
                f"    未平倉契約價值({value_unit}): {long_} {plain(p.long_oi_value)} / {short_} {plain(p.short_oi_value)} / "
                f"淨 {plain(p.net_oi_value)}"
            )
    return lines


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _query(gateway, contract: str, start_date: str, end_date: str):
        """Fetch rows for a contract code (server-side filter), a Chinese contract name
        (client-side filter over all contracts) or every contract.

        Returns (rows, label, not_found): ``not_found`` is the reply for a contract name with no
        match. A bad date range is an argument error and raises ``ToolError``."""
        contract = contract.strip()
        code = contract.upper() if contract and is_contract_code(contract) else ""
        rows, label, error = fetch_period(lambda s, e: gateway(_client, s, e, code), start_date, end_date,
                                          MAX_SPAN_DAYS)
        if error:
            raise ToolError(error)
        if rows is None:
            return None, label, None
        if contract and not code:
            matched = [r for r in rows if contract in r.contract]
            if not matched:
                names = "、".join(sorted({r.contract for r in rows}))
                return None, label, f"查無契約「{contract}」。{label} 可用契約：{names}"
            rows = matched
        return rows, label, None

    def _render(title: str, rows, label: str, value_unit: str, side_labels=("多", "空")) -> str:
        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date 或指定 contract")
        lines = [f"【{title}】{label}（共 {total} 筆{cap_note}）\n"]
        lines += format_trader_rows(shown, value_unit, side_labels)
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_futures(contract: str = "", start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢三大法人各期貨契約的交易與未平倉：預設最新交易日，也可回溯任意區間（最長 92 天）。

        回傳：自營商、投信、外資及陸資在各期貨契約的交易口數、交易金額（千元）、未平倉口數及契約價值（千元）

        Args:
            contract: 契約代碼（例如 TXF 臺股期貨、MXF 小型臺指、EXF 電子期貨）或中文名稱
                （例如「臺股期貨」）；留空＝全部契約。注意此處代碼與 get_daily_futures_market_report 的 TX/MTX 不同
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天
        """
        rows, label, not_found = _query(futures_contract_positions, contract, start_date, end_date)
        if not_found:
            return not_found
        if rows is None:
            return f"查無 {contract or '全部契約'} 在 {label} 的三大法人期貨資料，請確認契約代碼；日期也可能超出保存範圍（約近 3 年內）"
        return _render("三大法人期貨契約交易明細", rows, label, "千元")

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_options(contract: str = "", start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢三大法人各選擇權契約（買權+賣權合計）的交易與未平倉：預設最新交易日，也可回溯任意區間（最長 92 天）。
        買權、賣權分開請用 get_institutional_traders_calls_puts。

        回傳：自營商、投信、外資及陸資在各選擇權契約的交易口數、交易金額（千元）、未平倉口數及契約價值（千元）

        Args:
            contract: 契約代碼（例如 TXO 臺指選擇權）或中文名稱（例如「臺指選擇權」）；留空＝全部契約
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天
        """
        rows, label, not_found = _query(option_contract_positions, contract, start_date, end_date)
        if not_found:
            return not_found
        if rows is None:
            return f"查無 {contract or '全部契約'} 在 {label} 的三大法人選擇權資料，請確認契約代碼；日期也可能超出保存範圍（約近 3 年內）"
        return _render("三大法人選擇權契約交易明細", rows, label, "千元")

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_calls_puts(contract: str = "", call_put: str = "",
                                             start_date: TradingDate = "", end_date: TradingDate = "") -> str:
        """查詢三大法人選擇權買賣權分計（CALL 與 PUT 分開）：預設最新交易日，也可回溯任意區間（最長 92 天）。
        觀察法人對後市看法的重要指標，外資偏多時 CALL 淨買方未平倉通常增加。

        回傳：三大法人在各選擇權 CALL/PUT 的買方、賣方交易口數與金額（千元）、未平倉口數與契約價值（千元）

        Args:
            contract: 契約代碼（例如 TXO）或中文名稱（例如「臺指選擇權」）；留空＝全部契約
            call_put: 篩選 CALL 或 PUT，留空則顯示全部
            start_date: 起始日期 西元 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 西元 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天
        """
        rows, label, not_found = _query(calls_puts_positions, contract, start_date, end_date)
        if not_found:
            return not_found
        if rows is None:
            return f"查無 {contract or '全部契約'} 在 {label} 的三大法人買賣權分計資料，請確認契約代碼；日期也可能超出保存範圍（約近 3 年內）"
        if call_put.strip().upper() in ("CALL", "PUT"):
            rows = [r for r in rows if r.call_put.upper() == call_put.strip().upper()]
            if not rows:
                return f"查無 {contract or '全部契約'} 在 {label} 的 {call_put.upper()} 資料"
        return _render("三大法人選擇權買賣權分計", rows, label, "千元", side_labels=("買方", "賣方"))
