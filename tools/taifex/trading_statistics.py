"""TAIFEX annual and monthly trading volume statistics."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.taifex import TAIFEX_HEADERS

_ANNUAL_URL = "https://openapi.taifex.com.tw/v1/AnnualTradingVolume"
# Futures and options files have identical columns (verified 2026-10-18).
_MONTHLY_STATS_URLS = {
    "futures": ("期貨", "https://openapi.taifex.com.tw/v1/MonthlyTradingStatisticsFutures"),
    "options": ("選擇權", "https://openapi.taifex.com.tw/v1/MonthlyTradingStatisticsOptions"),
}


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
    def get_monthly_trading_statistics(market: str = "futures") -> str:
        """查詢期貨或選擇權市場上個月的交易人結構統計，依商品類別（股價指數、股票、商品、匯率）分類，
        顯示各類型交易人（散戶、自營商、投信、外資、期貨自營商）的買賣量與月底未平倉量。

        Args:
            market: futures（期貨，預設）或 options（選擇權）

        Returns:
            各商品類別的月統計交易量，依交易人別細分
        """
        if market not in _MONTHLY_STATS_URLS:
            return f"market 必須是 {'、'.join(_MONTHLY_STATS_URLS)} 其中之一"
        kind, url = _MONTHLY_STATS_URLS[market]
        data = _client.fetch_json(url, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return f"查無{kind}月統計資料"

        lines = [f"【{kind}市場月統計】（共 {len(data)} 筆）\n"]
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
