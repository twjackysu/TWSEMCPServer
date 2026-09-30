"""TAIFEX 三大法人 by contract (futures / options) and options by call-put, latest day or any period.

Source: www.taifex.com.tw download pages futContractsDateDown / optContractsDateDown /
callsAndPutsDateDown. These replace the openapi ...DetailsOfFuturesContracts /
...DetailsOfOptionsContracts / ...DetailsOfCallsAndPuts tools and the three former
*_history tools. On 2026-09-29 every openapi row matched these endpoints value for value,
and the futures page additionally carried 臺灣中型100期貨, which openapi omitted.
"""

from collections import OrderedDict
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, cap_rows
from utils.taifex import (
    TAIFEX_DOWNLOAD_BASE,
    TAIFEX_HEADERS,
    decode_and_parse_csv,
    download_form,
    fetch_period,
    is_contract_code,
)

FUT_CONTRACTS_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/futContractsDateDown"
OPT_CONTRACTS_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/optContractsDateDown"
CALLS_AND_PUTS_DATE_DOWN_URL = f"{TAIFEX_DOWNLOAD_BASE}/callsAndPutsDateDown"
# No server-enforced span cap observed (3-month pulls work); retention runs out ~3 years back.
MAX_SPAN_DAYS = 92
# Unfiltered futures are ~69 rows per day, so a 92-day span is ~6,000 rows.
MAX_OUTPUT_ROWS = 300


def format_trader_rows(rows: list, value_unit: str, offset: int = 0, side_labels=("多", "空")) -> list:
    """Render download-page rows grouped by date and contract.

    Futures/options-by-contract rows are 日期,商品名稱,身份別, then 12 numbers; calls/puts rows
    have 買賣權別 before 身份別, which ``offset=1`` accounts for.
    """
    long_, short_ = side_labels
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for r in rows:
        key = (r[0], r[1]) + ((r[2],) if offset else ())
        groups.setdefault(key, []).append(r)
    lines = []
    for key, items in groups.items():
        lines.append(f"▶ {' '.join(key)}")
        for r in items:
            n = r[3 + offset:]
            # n: 多方交易口數,多方交易契約金額,空方交易口數,空方交易契約金額,淨口數,淨金額,
            #    多方未平倉口數,多方未平倉契約金額,空方未平倉口數,空方未平倉契約金額,淨未平倉口數,淨未平倉金額
            lines.append(
                f"  {r[2 + offset]}\n"
                f"    交易量: {long_} {n[0]} / {short_} {n[2]} / 淨 {n[4]}\n"
                f"    交易金額({value_unit}): {long_} {n[1]} / {short_} {n[3]} / 淨 {n[5]}\n"
                f"    未平倉口數: {long_} {n[6]} / {short_} {n[8]} / 淨 {n[10]}\n"
                f"    未平倉契約價值({value_unit}): {long_} {n[7]} / {short_} {n[9]} / 淨 {n[11]}"
            )
    return lines


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    def _query(url: str, contract: str, start_date: str, end_date: str):
        """Fetch rows for a contract code (server-side filter), a Chinese contract name
        (client-side filter over all contracts) or every contract."""
        contract = contract.strip()
        code = contract.upper() if contract and is_contract_code(contract) else ""

        def fetch(start_dt, end_dt):
            body = _client.fetch_bytes(
                url,
                method="POST",
                headers=TAIFEX_HEADERS,
                data=download_form(start_dt, end_dt, commodityId=code),
            )
            return decode_and_parse_csv(body)

        parsed, label, error = fetch_period(fetch, start_date, end_date, MAX_SPAN_DAYS, "20260401")
        if error or parsed is None:
            return None, label, error
        rows = parsed[1]
        if contract and not code:
            matched = [r for r in rows if contract in r[1]]
            if not matched:
                names = "、".join(sorted({r[1] for r in rows}))
                return None, label, f"查無契約「{contract}」。{label} 可用契約：{names}"
            rows = matched
        return rows, label, None

    def _render(title: str, rows, label: str, value_unit: str, offset: int = 0, side_labels=("多", "空")) -> str:
        total = len(rows)
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS, "請縮小 start_date～end_date 或指定 contract")
        lines = [f"【{title}】{label}（共 {total} 筆{cap_note}）\n"]
        lines += format_trader_rows(shown, value_unit, offset, side_labels)
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_futures(contract: str = "", start_date: str = "", end_date: str = "") -> str:
        """查詢三大法人各期貨契約的交易與未平倉：預設最新交易日，也可回溯任意區間（最長 92 天）。

        Args:
            contract: 契約代碼（例如 TXF 臺股期貨、MXF 小型臺指、EXF 電子期貨）或中文名稱
                （例如「臺股期貨」）；留空＝全部契約。注意此處代碼與 get_daily_futures_market_report 的 TX/MTX 不同
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天

        Returns:
            自營商、投信、外資及陸資在各期貨契約的交易口數、交易金額（千元）、未平倉口數及契約價值（千元）
        """
        rows, label, error = _query(FUT_CONTRACTS_DATE_DOWN_URL, contract, start_date, end_date)
        if error:
            return error
        if rows is None:
            return f"查無 {contract or '全部契約'} 在 {label} 的三大法人期貨資料，請確認契約代碼；日期也可能超出保存範圍（約近 3 年內）"
        return _render("三大法人期貨契約交易明細", rows, label, "千元")

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_options(contract: str = "", start_date: str = "", end_date: str = "") -> str:
        """查詢三大法人各選擇權契約（買權+賣權合計）的交易與未平倉：預設最新交易日，也可回溯任意區間（最長 92 天）。
        買權、賣權分開請用 get_institutional_traders_calls_puts。

        Args:
            contract: 契約代碼（例如 TXO 臺指選擇權）或中文名稱（例如「臺指選擇權」）；留空＝全部契約
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天

        Returns:
            自營商、投信、外資及陸資在各選擇權契約的交易口數、交易金額（千元）、未平倉口數及契約價值（千元）
        """
        rows, label, error = _query(OPT_CONTRACTS_DATE_DOWN_URL, contract, start_date, end_date)
        if error:
            return error
        if rows is None:
            return f"查無 {contract or '全部契約'} 在 {label} 的三大法人選擇權資料，請確認契約代碼；日期也可能超出保存範圍（約近 3 年內）"
        return _render("三大法人選擇權契約交易明細", rows, label, "千元")

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_calls_puts(contract: str = "", call_put: str = "",
                                             start_date: str = "", end_date: str = "") -> str:
        """查詢三大法人選擇權買賣權分計（CALL 與 PUT 分開）：預設最新交易日，也可回溯任意區間（最長 92 天）。
        觀察法人對後市看法的重要指標，外資偏多時 CALL 淨買方未平倉通常增加。

        Args:
            contract: 契約代碼（例如 TXO）或中文名稱（例如「臺指選擇權」）；留空＝全部契約
            call_put: 篩選 CALL 或 PUT，留空則顯示全部
            start_date: 起始日期 YYYYMMDD（選填，留空＝最新交易日）
            end_date: 結束日期 YYYYMMDD（選填，預設同 start_date）。區間不可超過 92 天

        Returns:
            三大法人在各選擇權 CALL/PUT 的買方、賣方交易口數與金額（千元）、未平倉口數與契約價值（千元）
        """
        rows, label, error = _query(CALLS_AND_PUTS_DATE_DOWN_URL, contract, start_date, end_date)
        if error:
            return error
        if rows is None:
            return f"查無 {contract or '全部契約'} 在 {label} 的三大法人買賣權分計資料，請確認契約代碼；日期也可能超出保存範圍（約近 3 年內）"
        if call_put.strip().upper() in ("CALL", "PUT"):
            rows = [r for r in rows if r[2].strip().upper() == call_put.strip().upper()]
            if not rows:
                return f"查無 {contract or '全部契約'} 在 {label} 的 {call_put.upper()} 資料"
        return _render("三大法人選擇權買賣權分計", rows, label, "千元", offset=1, side_labels=("買方", "賣方"))
