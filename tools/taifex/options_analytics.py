"""TAIFEX options analytics: delta values and open interest change."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

_DELTA_URL = "https://openapi.taifex.com.tw/v1/DailyOptionsDelta"
_OI_CHANGE_URL = "https://openapi.taifex.com.tw/v1/va01"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_options_delta(
        contract: str = "TXO",
        contract_month: str = "",
        call_put: str = "",
    ) -> str:
        """查詢選擇權每日 Delta 值，可用於了解各履約價的風險敏感度與隱含方向性。
        Delta 接近 1（或 -1）代表深度價內，接近 0 代表深度價外。
        因資料量龐大（TXO 每月逾 200 筆），建議指定 contract_month 縮小範圍。

        Args:
            contract: 選擇權契約代碼，預設 TXO。留空則列出所有可用契約代碼。
            contract_month: 到期月份/週次，例如「202605」或「202605W1」。留空則列出可用月份。
            call_put: 篩選「買權」或「賣權」，留空則顯示全部。

        Returns:
            指定條件下各履約價的 Delta 值與到期日
        """
        data = _client.fetch_json(_DELTA_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無選擇權 Delta 資料"

        if not contract:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"可用選擇權契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

        contract = contract.upper()
        filtered = [x for x in data if x.get("Contract") == contract]

        if not filtered:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"查無契約 {contract}。可用代碼：{', '.join(contracts[:30])}"

        if not contract_month:
            months = sorted(set(x.get("ContractMonth(Week)", "") for x in filtered))
            return (
                f"契約 {contract} 可用到期月份（共 {len(months)} 個）：\n"
                + "、".join(months)
                + "\n請指定 contract_month 參數以查詢 Delta 值。"
            )

        filtered = [x for x in filtered if x.get("ContractMonth(Week)") == contract_month]
        if not filtered:
            return f"查無 {contract} 在月份 {contract_month} 的 Delta 資料"

        if call_put in ("買權", "賣權"):
            filtered = [x for x in filtered if x.get("CallPut") == call_put]

        settle_day = filtered[0].get("ContractSettlementDay", "?")
        lines = [
            f"【選擇權 Delta 值】{contract} | 到期月份:{contract_month} | 結算日:{settle_day}\n"
        ]

        for item in filtered:
            cp = item.get("CallPut", "?")
            strike = item.get("StrikePrice", "?")
            delta = item.get("Delta", "?")
            lines.append(f"  {cp} 履約價:{strike:>8}  Delta:{delta}")

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_options_oi_change() -> str:
        """查詢台指選擇權每日未平倉量增減，顯示今日與前一交易日的未平倉量及變化量。
        未平倉大幅增加代表新部位建立，大幅減少代表部位了結或到期。

        Returns:
            今日未平倉量、前一交易日未平倉量及增減變化
        """
        data = _client.fetch_json(_OI_CHANGE_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無台指選擇權未平倉量增減資料"

        item = data[0]
        date = item.get("Date", "?")
        oi = item.get("OpenInterest", "-")
        prev_day = item.get("PreviousDay", "?")
        prev_oi = item.get("PreviousDayOpenInterest", "-")
        change = item.get("Change", "-")

        try:
            change_int = int(change)
            direction = "▲" if change_int > 0 else ("▼" if change_int < 0 else "─")
        except (ValueError, TypeError):
            direction = ""

        return (
            f"【台指選擇權每日未平倉量增減】\n\n"
            f"今日（{date}）未平倉量：{oi}\n"
            f"前一交易日（{prev_day}）未平倉量：{prev_oi}\n"
            f"增減：{direction} {change}"
        )
