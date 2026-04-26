"""TAIFEX annual and monthly trading volume statistics."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

_ANNUAL_URL = "https://openapi.taifex.com.tw/v1/AnnualTradingVolume"
_MONTHLY_STATS_URL = "https://openapi.taifex.com.tw/v1/MonthlyTradingStatisticsFutures"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_annual_trading_volume(contract: str = "") -> str:
        """查詢各期貨商品年成交量統計，包含年度總成交量、交易日數及平均日成交量。
        可用於長期趨勢分析與商品流動性比較。
        留空 contract 則顯示全部商品。

        Args:
            contract: 期貨契約代碼，例如 TX、MTX。留空則顯示全部。

        Returns:
            各商品年度成交量、交易日數、平均每日成交量
        """
        data = _client.fetch_json(_ANNUAL_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無年成交量統計資料"

        if contract:
            contract = contract.upper()
            filtered = [x for x in data if x.get("Contract", "").upper() == contract]
            if not filtered:
                contracts = sorted(set(x.get("Contract", "") for x in data))
                return f"查無契約 {contract}。可用代碼：{', '.join(contracts)}"
            data = filtered

        lines = [f"【各期貨商品年成交量統計】（共 {len(data)} 筆）\n"]
        for item in data:
            year = item.get("YYYY", "?")
            code = item.get("Contract", "?")
            name = item.get("ContractName", "?")
            vol = item.get("Volume", "-")
            days = item.get("NumberOfTradingDays", "-")
            avg = item.get("AvgDailyTradingVolume", "-")
            lines.append(
                f"[{year}] {code}（{name}）\n"
                f"  年成交量:{vol}  交易日數:{days}  平均日成交量:{avg}"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_monthly_trading_statistics() -> str:
        """查詢期貨市場月統計資料，依商品類別（股價指數、利率、商品、股票）分類，
        顯示各類型交易人（自營商、投信、外資、散戶等）的買賣量與月底未平倉量。

        Returns:
            各期貨商品類別的月統計交易量，依交易人別細分
        """
        data = _client.fetch_json(_MONTHLY_STATS_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無期貨月統計資料"

        lines = [f"【期貨市場月統計】（共 {len(data)} 筆）\n"]
        for item in data:
            ym = item.get("YYYYMM", "?")
            name = item.get("ContactName", "?")
            total = item.get("TotalVolume", "-")
            month_end_oi = item.get("MonthEndOpenInterest", "-")

            ind_buy = item.get("Brokers-Individual(Buy)", "-")
            ind_sell = item.get("Brokers-Individual(Sell)", "-")
            dealer_buy = item.get("Brokers-InstutionalInvestors-SecuritiesDealers(Buy)", "-")
            dealer_sell = item.get("Brokers-InstutionalInvestors-SecuritiesDealers(Sell)", "-")
            sit_buy = item.get("Brokers-InstutionalInvestors-SecuritiesInvestmentTrust(Buy)", "-")
            sit_sell = item.get("Brokers-InstutionalInvestors-SecuritiesInvestmentTrust(Sell)", "-")
            foreign_buy = item.get("Brokers-InstutionalInvestors-Foreign&MainlandAreaInstitutionalInvestors(Buy)", "-")
            foreign_sell = item.get("Brokers-InstutionalInvestors-Foreign&MainlandAreaInstitutionalInvestors(Sell)", "-")
            prop_buy = item.get("ProprietaryTraders(Buy)", "-")
            prop_sell = item.get("ProprietaryTraders(Sell)", "-")

            lines.append(
                f"▶ [{ym}] {name}  總成交量:{total}  月底未平倉:{month_end_oi}\n"
                f"  散戶: 買 {ind_buy} / 賣 {ind_sell}\n"
                f"  自營商: 買 {prop_buy} / 賣 {prop_sell}\n"
                f"  投信: 買 {sit_buy} / 賣 {sit_sell}\n"
                f"  外資: 買 {foreign_buy} / 賣 {foreign_sell}\n"
                f"  期貨自營商: 買 {dealer_buy} / 賣 {dealer_sell}"
            )
        return "\n".join(lines)
