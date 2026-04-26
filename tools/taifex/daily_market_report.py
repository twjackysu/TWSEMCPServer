"""TAIFEX daily futures and options market report."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

TAIFEX_FUT_REPORT_URL = "https://openapi.taifex.com.tw/v1/DailyMarketReportFut"
TAIFEX_OPT_REPORT_URL = "https://openapi.taifex.com.tw/v1/DailyMarketReportOpt"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_daily_futures_market_report(contract: str = "TX") -> str:
        """查詢期貨每日交易行情，包含開高低收、成交量、未平倉量等資訊。
        常用契約代碼：TX（臺指期貨）、MTX（小型臺指）、ZEF（電子期貨）、ZTF（金融期貨）。
        留空 contract 可列出所有可用契約代碼。

        Args:
            contract: 期貨契約代碼，例如 TX、MTX。留空則列出所有可用契約代碼。

        Returns:
            指定契約的每日交易行情，包含各到期月份及一般／盤後交易時段資料
        """
        data = _client.fetch_json(TAIFEX_FUT_REPORT_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無期貨每日交易行情資料"

        if not contract:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"可用期貨契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

        contract = contract.upper()
        filtered = [x for x in data if x.get("Contract") == contract]

        if not filtered:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"查無契約代碼 {contract} 的資料。可用代碼：{', '.join(contracts[:30])}"

        date = filtered[0].get("Date", "?")
        lines = [f"【期貨每日交易行情】{contract} | {date}\n"]

        for item in filtered:
            month = item.get("ContractMonth(Week)", "?")
            session = item.get("TradingSession", "")
            open_ = item.get("Open", "-")
            high = item.get("High", "-")
            low = item.get("Low", "-")
            last = item.get("Last", "-")
            change = item.get("Change", "-")
            pct = item.get("%", "-")
            vol = item.get("Volume", "-")
            oi = item.get("OpenInterest", "-")
            settle = item.get("SettlementPrice", "-")
            bid = item.get("BestBid", "-")
            ask = item.get("BestAsk", "-")

            lines.append(
                f"[{month}]（{session}）\n"
                f"  開:{open_} 高:{high} 低:{low} 收:{last} 漲跌:{change}（{pct}）\n"
                f"  成交量:{vol} 未平倉:{oi} 結算價:{settle}\n"
                f"  最佳買:{bid} 最佳賣:{ask}"
            )

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_daily_options_market_report(
        contract: str = "TXO",
        call_put: str = "",
        limit: int = 30,
    ) -> str:
        """查詢選擇權每日交易行情，篩選有成交量的履約價資料，按成交量排序。
        常用契約代碼：TXO（臺指選擇權）、TEO（電子選擇權）、TFO（金融選擇權）。
        留空 contract 可列出所有可用契約代碼。

        Args:
            contract: 選擇權契約代碼，例如 TXO。留空則列出所有可用契約代碼。
            call_put: 篩選買賣權，填「買權」或「賣權」，留空則顯示全部。
            limit: 顯示筆數上限（按成交量由大到小），預設 30。

        Returns:
            有成交量的選擇權每日交易行情，按成交量由大到小排列
        """
        data = _client.fetch_json(TAIFEX_OPT_REPORT_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無選擇權每日交易行情資料"

        if not contract:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"可用選擇權契約代碼（共 {len(contracts)} 種）：\n" + "、".join(contracts)

        contract = contract.upper()
        filtered = [x for x in data if x.get("Contract") == contract]

        if not filtered:
            contracts = sorted(set(x.get("Contract", "") for x in data))
            return f"查無契約代碼 {contract} 的資料。可用代碼：{', '.join(contracts[:30])}"

        if call_put in ("買權", "賣權"):
            filtered = [x for x in filtered if x.get("CallPut") == call_put]

        with_volume = [x for x in filtered if x.get("Volume", "0") != "0"]

        try:
            with_volume.sort(key=lambda x: int(x.get("Volume", "0")), reverse=True)
        except (ValueError, TypeError):
            pass

        total = len(with_volume)
        shown = with_volume[:limit]
        date = filtered[0].get("Date", "?") if filtered else "?"

        lines = [
            f"【選擇權每日交易行情】{contract} | {date}",
            f"有成交量共 {total} 筆，顯示前 {len(shown)} 筆（按成交量排序）\n",
        ]

        for item in shown:
            month = item.get("ContractMonth(Week)", "?")
            strike = item.get("StrikePrice", "?")
            cp = item.get("CallPut", "?")
            open_ = item.get("Open", "-")
            high = item.get("High", "-")
            low = item.get("Low", "-")
            close = item.get("Close", "-")
            vol = item.get("Volume", "-")
            oi = item.get("OpenInterest", "-")
            settle = item.get("SettlementPrice", "-")
            session = item.get("TradingSession", "")

            lines.append(
                f"[{month}] {cp} 履約:{strike}（{session}）\n"
                f"  開:{open_} 高:{high} 低:{low} 收:{close}\n"
                f"  成交量:{vol} 未平倉:{oi} 結算價:{settle}"
            )

        return "\n".join(lines)
