"""TAIFEX large traders open interest data."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

TAIFEX_LT_FUT_URL = "https://openapi.taifex.com.tw/v1/OpenInterestOfLargeTradersFutures"
TAIFEX_LT_OPT_URL = "https://openapi.taifex.com.tw/v1/OpenInterestOfLargeTradersOptions"

_TYPE_LABELS = {"0": "所有交易人", "1": "特定法人"}
_SETTLE_LABELS = {"666666": "所有月份合計", "999912": "所有月份總計"}


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_futures_oi(contract: str = "TX") -> str:
        """查詢期貨大額交易人（前五大、前十大）未沖銷部位資料，可觀察大戶持倉方向。
        前五大、前十大部位集中度越高，代表市場籌碼越集中。
        常用契約：TX（臺股期貨，含 MTX 折算）。

        Args:
            contract: 期貨契約代碼，預設 TX。留空則列出所有可用契約代碼。

        Returns:
            前五大／前十大交易人的多空部位及市場總未平倉，區分所有交易人與特定法人
        """
        data = _client.fetch_json(TAIFEX_LT_FUT_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無期貨大額交易人未沖銷部位資料"

        if not contract:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"可用期貨契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

        contract = contract.upper()
        filtered = [x for x in data if x.get("Contract") == contract]

        if not filtered:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"查無契約 {contract} 的資料。可用代碼：{', '.join(contracts[:30])}"

        date = filtered[0].get("Date", "?")
        name = filtered[0].get("ContractName", contract)
        lines = [f"【期貨大額交易人未沖銷部位】{contract}（{name}）| {date}\n"]

        for item in filtered:
            settle_month = item.get("SettlementMonth", "?")
            month_label = _SETTLE_LABELS.get(settle_month, f"到期月 {settle_month}")
            type_label = _TYPE_LABELS.get(item.get("TypeOfTraders", ""), "?")
            top5_buy = item.get("Top5Buy", "-")
            top5_sell = item.get("Top5Sell", "-")
            top10_buy = item.get("Top10Buy", "-")
            top10_sell = item.get("Top10Sell", "-")
            oi_market = item.get("OIOfMarket", "-")

            lines.append(
                f"[{month_label}] {type_label}\n"
                f"  前五大: 多 {top5_buy} / 空 {top5_sell}\n"
                f"  前十大: 多 {top10_buy} / 空 {top10_sell}\n"
                f"  市場總未平倉: {oi_market}"
            )

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_large_traders_options_oi(contract: str = "TXO", call_put: str = "") -> str:
        """查詢選擇權大額交易人（前五大、前十大）未沖銷部位資料，可觀察大戶選擇權布局。
        常用契約：TXO（臺指選擇權）。

        Args:
            contract: 選擇權契約代碼，預設 TXO。留空則列出所有可用契約代碼。
            call_put: 篩選買賣權，填「買權」或「賣權」，留空則顯示全部。

        Returns:
            前五大／前十大交易人的買賣權多空部位，區分所有交易人與特定法人
        """
        data = _client.fetch_json(TAIFEX_LT_OPT_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無選擇權大額交易人未沖銷部位資料"

        if not contract:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"可用選擇權契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

        contract = contract.upper()
        filtered = [x for x in data if x.get("Contract") == contract]

        if not filtered:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"查無契約 {contract} 的資料。可用代碼：{', '.join(contracts[:30])}"

        if call_put in ("買權", "賣權"):
            filtered = [x for x in filtered if x.get("CallPut") == call_put]

        date = filtered[0].get("Date", "?")
        name = filtered[0].get("ContractName", contract)
        lines = [f"【選擇權大額交易人未沖銷部位】{contract}（{name}）| {date}\n"]

        for item in filtered:
            cp = item.get("CallPut", "?")
            settle_month = item.get("SettlementMonth", "?")
            month_label = _SETTLE_LABELS.get(settle_month, f"到期月 {settle_month}")
            type_label = _TYPE_LABELS.get(item.get("TypeOfTraders", ""), "?")
            top5_buy = item.get("Top5Buy", "-")
            top5_sell = item.get("Top5Sell", "-")
            top10_buy = item.get("Top10Buy", "-")
            top10_sell = item.get("Top10Sell", "-")
            oi_market = item.get("OIOfMarket", "-")

            lines.append(
                f"[{cp}][{month_label}] {type_label}\n"
                f"  前五大: 多 {top5_buy} / 空 {top5_sell}\n"
                f"  前十大: 多 {top10_buy} / 空 {top10_sell}\n"
                f"  市場總未平倉: {oi_market}"
            )

        return "\n".join(lines)
