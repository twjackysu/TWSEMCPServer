"""TAIFEX institutional traders details by contract and by call/put."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from .futures_position import TAIFEX_HEADERS

_FUT_DETAILS_URL = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate"
_OPT_DETAILS_URL = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDetailsOfOptionsContractsBytheDate"
_CALLS_PUTS_URL = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDetailsOfCallsAndPutsBytheDate"


def _format_trader_block(item: dict, show_call_put: bool = False) -> str:
    investor = item.get("Item", "?")
    cp = f"[{item.get('CallPut', '?')}] " if show_call_put else ""
    tv_long = item.get("TradingVolume(Long)", "-")
    tv_short = item.get("TradingVolume(Short)", "-")
    tv_net = item.get("TradingVolume(Net)", "-")
    val_long = item.get("TradingValue(Long)(Thousands)", "-")
    val_short = item.get("TradingValue(Short)(Thousands)", "-")
    val_net = item.get("TradingValue(Net)(Thousands)", "-")
    oi_long = item.get("OpenInterest(Long)", "-")
    oi_short = item.get("OpenInterest(Short)", "-")
    oi_net = item.get("OpenInterest(Net)", "-")
    cv_long = item.get("ContractValueofOpenInterest(Long)(Thousands)", "-")
    cv_short = item.get("ContractValueofOpenInterest(Short)(Thousands)", "-")
    cv_net = item.get("ContractValueofOpenInterest(Net)(Thousands)", "-")
    return (
        f"  {cp}{investor}\n"
        f"    交易量: 多 {tv_long} / 空 {tv_short} / 淨 {tv_net}\n"
        f"    交易金額(千): 多 {val_long} / 空 {val_short} / 淨 {val_net}\n"
        f"    未平倉口數: 多 {oi_long} / 空 {oi_short} / 淨 {oi_net}\n"
        f"    未平倉契約價值(千): 多 {cv_long} / 空 {cv_short} / 淨 {cv_net}"
    )


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_futures(contract_code: str = "") -> str:
        """查詢三大法人依各期貨契約分類的交易資料，可觀察各期貨商品的法人買賣情況。
        留空 contract_code 可列出所有可用契約名稱。

        Args:
            contract_code: 期貨契約名稱（中文），例如「臺股期貨」。留空則顯示全部。

        Returns:
            三大法人（自營商、投信、外資）在各期貨契約的交易量、金額（千元）及未平倉資訊
        """
        data = _client.fetch_json(_FUT_DETAILS_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無三大法人期貨契約交易資料"

        date = data[0].get("Date", "?")

        if contract_code:
            filtered = [x for x in data if contract_code in x.get("ContractCode", "")]
            if not filtered:
                contracts = sorted(set(x.get("ContractCode", "") for x in data))
                return f"查無契約「{contract_code}」。可用契約：\n" + "\n".join(contracts)
            data = filtered

        contracts_map: dict[str, list] = {}
        for item in data:
            code = item.get("ContractCode", "?")
            contracts_map.setdefault(code, []).append(item)

        lines = [f"【三大法人期貨契約交易明細】{date}\n"]
        for code, items in contracts_map.items():
            lines.append(f"▶ {code}")
            for item in items:
                lines.append(_format_trader_block(item))
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_by_options(contract_code: str = "") -> str:
        """查詢三大法人依各選擇權契約分類的交易資料，可觀察各選擇權商品的法人買賣情況。
        留空 contract_code 可列出所有可用契約名稱。

        Args:
            contract_code: 選擇權契約名稱（中文），例如「臺指選擇權」。留空則顯示全部。

        Returns:
            三大法人在各選擇權契約的交易量、金額（千元）及未平倉資訊
        """
        data = _client.fetch_json(_OPT_DETAILS_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無三大法人選擇權契約交易資料"

        date = data[0].get("Date", "?")

        if contract_code:
            filtered = [x for x in data if contract_code in x.get("ContractCode", "")]
            if not filtered:
                contracts = sorted(set(x.get("ContractCode", "") for x in data))
                return f"查無契約「{contract_code}」。可用契約：\n" + "\n".join(contracts)
            data = filtered

        contracts_map: dict[str, list] = {}
        for item in data:
            code = item.get("ContractCode", "?")
            contracts_map.setdefault(code, []).append(item)

        lines = [f"【三大法人選擇權契約交易明細】{date}\n"]
        for code, items in contracts_map.items():
            lines.append(f"▶ {code}")
            for item in items:
                lines.append(_format_trader_block(item))
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_institutional_traders_calls_puts(
        contract_code: str = "",
        call_put: str = "",
    ) -> str:
        """查詢三大法人選擇權買賣權分計交易資料，分別顯示 CALL 與 PUT 的法人持倉情況。
        此為觀察法人對後市看法的重要指標，外資偏多時 CALL 淨多單會大幅增加。

        Args:
            contract_code: 選擇權契約名稱（中文），例如「臺指選擇權」。留空則顯示全部。
            call_put: 篩選 CALL 或 PUT，留空則顯示全部。

        Returns:
            三大法人在各選擇權 CALL/PUT 的交易量、金額（千元）及未平倉資訊
        """
        data = _client.fetch_json(_CALLS_PUTS_URL, headers=TAIFEX_HEADERS)

        if not isinstance(data, list) or not data:
            return "查無三大法人選擇權買賣權分計資料"

        date = data[0].get("Date", "?")

        if contract_code:
            data = [x for x in data if contract_code in x.get("ContractCode", "")]
        if call_put.upper() in ("CALL", "PUT"):
            data = [x for x in data if x.get("CallPut", "").upper() == call_put.upper()]

        if not data:
            return f"查無符合條件的資料（contract_code={contract_code}, call_put={call_put}）"

        contracts_map: dict[str, list] = {}
        for item in data:
            code = item.get("ContractCode", "?")
            contracts_map.setdefault(code, []).append(item)

        lines = [f"【三大法人選擇權買賣權分計】{date}\n"]
        for code, items in contracts_map.items():
            lines.append(f"▶ {code}")
            for item in items:
                lines.append(_format_trader_block(item, show_call_put=True))
        return "\n".join(lines)
