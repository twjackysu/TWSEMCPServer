"""TAIFEX general institutional investors trading data (futures + options combined)."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

TAIFEX_IG_URL = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_institutional_general() -> str:
        """查詢三大法人（自營商、投信、外資）當日期貨與選擇權市場整體交易總表。
        與 get_futures_institutional 不同，本工具涵蓋期貨與選擇權合計的整體數據，
        包含交易量、交易金額（百萬元）、未平倉口數及契約價值。

        Returns:
            三大法人的整體交易量（多/空/淨）、交易金額、未平倉口數及契約價值（百萬元）
        """
        data = _client.fetch_json(TAIFEX_IG_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無三大法人整體交易資料"

        date = data[0].get("Date", "?")
        lines = [f"【三大法人整體交易總表（期貨+選擇權）】{date}\n"]

        for item in data:
            investor = item.get("Item", "?")
            tv_long = item.get("TradingVolume(Long)", "-")
            tv_short = item.get("TradingVolume(Short)", "-")
            tv_net = item.get("TradingVolume(Net)", "-")
            val_long = item.get("TradingValue(Long)(Millions)", "-")
            val_short = item.get("TradingValue(Short)(Millions)", "-")
            val_net = item.get("TradingValue(Net)(Millions)", "-")
            oi_long = item.get("OpenInterest(Long)", "-")
            oi_short = item.get("OpenInterest(Short)", "-")
            oi_net = item.get("OpenInterest(Net)", "-")
            cv_long = item.get("ContractValueOfOpenInterest(Long)(Millions)", "-")
            cv_short = item.get("ContractValueOfOpenInterest(Short)(Millions)", "-")
            cv_net = item.get("ContractValueOfOpenInterest(Net)(Millions)", "-")

            lines.append(
                f"【{investor}】\n"
                f"  交易量: 多 {tv_long} / 空 {tv_short} / 淨 {tv_net}\n"
                f"  交易金額(百萬): 多 {val_long} / 空 {val_short} / 淨 {val_net}\n"
                f"  未平倉口數: 多 {oi_long} / 空 {oi_short} / 淨 {oi_net}\n"
                f"  未平倉契約價值(百萬): 多 {cv_long} / 空 {cv_short} / 淨 {cv_net}"
            )

        return "\n".join(lines)
