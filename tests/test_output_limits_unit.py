"""清單型工具的輸出上限（不打網路）。

這些工具原本把整份資料 join 成單一字串回傳，實測 get_warrant_basic_info 產出
37.85 MB、get_warrant_yearly_issuance_statistics 8.18M 字元、
get_daily_options_market_report 指定 contract_month 後仍有 2.65 MB——遠超任何模型的
context window。此處以「字元數天花板」為斷言，避免日後有人拿掉分頁。

假資料的筆數都刻意設成「沒分頁就會超過 MAX_CHARS」，所以斷言失敗只可能是分頁被拿掉。
"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
import tools.trading.warrants as warrants
import tools.history.margin_balance as margin_balance
import tools.history.bwibbu_all as bwibbu_all
import tools.taifex.daily_market_report as daily_market_report
import tools.taifex.institutional_details as institutional_details

pytestmark = pytest.mark.offline

# 寬鬆的上限：只要沒有分頁就會超出好幾個數量級，不必抓得太緊
MAX_CHARS = 100_000
ROWS = 3000
TRADING_DATE = "20250102"


def _warrant_basic(i):
    return {
        "出表日期": "1150927",
        "權證代號": f"{i:06d}",
        "權證簡稱": f"測試權證{i}",
        "權證類型": "認購",
        "類別": "一般型",
        "標的證券/指數": "2330",
        "最新履約價格(元)/履約指數": "1000.00",
        "最後交易日": "1151231",
        # 真實資料的「備註」是逐筆增額/註銷流水帳，單筆可逾千字
        "備註": "增額發行紀錄。" * 150,
    }


def _warrant_generic(i):
    return {f"欄位{k}": f"{i}-{k}-值" for k in range(10)}


WARRANT_ROUTES = {
    "/opendata/t187ap37_L": [_warrant_basic(i) for i in range(ROWS)],
    "/opendata/t187ap42_L": [_warrant_generic(i) for i in range(ROWS)],
    "/opendata/t187ap36_L": [_warrant_generic(i) for i in range(ROWS)],
}


@pytest.fixture
def warrant_tools():
    return register_module_tools(warrants, OfflineClient(WARRANT_ROUTES))


@pytest.mark.parametrize(
    "tool_name",
    [
        "get_warrant_basic_info",
        "get_warrant_daily_trading",
        "get_warrant_yearly_issuance_statistics",
    ],
)
def test_warrant_list_tools_are_bounded(warrant_tools, tool_name):
    """權證三支清單工具不指定 code 時仍須分頁."""
    result = warrant_tools[tool_name]()
    assert len(result) < MAX_CHARS, f"{tool_name} 輸出 {len(result):,} 字元，未分頁"
    assert f"共有 {ROWS} 筆" in result, "應回報總筆數"


def test_warrant_basic_list_omits_remarks(warrant_tools):
    """清單模式省略「備註」；指定 code 時才回傳完整欄位."""
    assert "增額發行紀錄" not in warrant_tools["get_warrant_basic_info"]()
    assert "增額發行紀錄" in warrant_tools["get_warrant_basic_info"](code="000007")


def test_warrant_pagination_advances(warrant_tools):
    """offset 必須真的換頁."""
    first = warrant_tools["get_warrant_basic_info"](limit=5)
    second = warrant_tools["get_warrant_basic_info"](limit=5, offset=5)
    assert first != second, "offset 未生效，兩頁內容相同"
    assert "000005" in second and "000005" not in first


@pytest.fixture
def margin_tools():
    fields = ["代號", "名稱"] + [f"欄位{k}" for k in range(14)]
    rows = [[f"{1000 + i}", f"股票{i}"] + ["1,234,567"] * 14 for i in range(ROWS)]
    resp = {"stat": "OK", "tables": [{"data": []}, {"fields": fields, "data": rows}]}
    return register_module_tools(margin_balance, OfflineClient({"/exchangeReport/MI_MARGN": resp}))


def test_margin_balance_is_bounded(margin_tools):
    result = margin_tools["get_margin_balance"](TRADING_DATE)
    assert len(result) < MAX_CHARS, f"輸出 {len(result):,} 字元，未分頁"
    assert "offset=" in result, "未提示如何取得後續資料"


def test_margin_balance_offset_out_of_range_is_explicit(margin_tools):
    result = margin_tools["get_margin_balance"](TRADING_DATE, offset=999_999)
    assert "超出範圍" in result, f"offset 越界未給明確訊息: {result[:120]!r}"


@pytest.fixture
def valuation_tools():
    rows = [[f"{1000 + i}", f"股票{i}", "123.45", "3.21", "113", "15.67", "2.34", "114/2"] for i in range(ROWS)]
    resp = {"stat": "OK", "date": TRADING_DATE, "data": rows}
    return register_module_tools(bwibbu_all, OfflineClient({"/afterTrading/BWIBBU_d": resp}))


def test_market_valuation_is_bounded(valuation_tools):
    result = valuation_tools["get_stock_valuation_ratios"](TRADING_DATE)
    assert len(result) < MAX_CHARS, f"輸出 {len(result):,} 字元，未分頁"
    assert "offset=" in result, "未提示如何取得後續資料"


def test_market_valuation_offset_out_of_range_is_explicit(valuation_tools):
    result = valuation_tools["get_stock_valuation_ratios"](TRADING_DATE, offset=999_999)
    assert "超出範圍" in result, f"offset 越界未給明確訊息: {result[:120]!r}"


def _big5_csv(header, rows):
    lines = [",".join(header)] + [",".join(r) for r in rows]
    return ("\r\n".join(lines) + "\r\n").encode("big5")


class TestTaifexHistoryOutputLimits:
    """歷史下載類工具的輸出上限。

    這兩支從 www.taifex.com.tw 下載多日 CSV，沒有伺服器端分頁。
    選擇權行情（原 get_options_daily_history）原本的保護帶了 `not contract_month`，
    而 docstring 又建議指定 contract_month——正好把呼叫者推進唯一沒有保護的
    分支（實測單月 TXO 單一到期月仍有 23,032 列 / 2.65 MB）。
    """

    def test_options_market_report_is_bounded_with_contract_month(self):
        # 真實 header 尾端多一個逗號，欄位數比資料列多 1
        header = [
            "交易日期", "契約", "到期月份(週別)", "履約價", "買賣權", "開盤價", "最高價", "最低價",
            "收盤價", "成交量", "結算價", "未沖銷契約數", "最後最佳買價", "最後最佳賣價",
            "歷史最高價", "歷史最低價", "是否因訊息面暫停交易", "交易時段", "",
        ]
        rows = [
            ["2025/06/02", "TXO", "202507", str(15000 + i), "買權", "100", "110", "90", "105",
             "1234", "104", "5678", "-", "-", "-", "-", "", "一般"]
            for i in range(ROWS)
        ]
        client = OfflineClient({"/cht/3/optDataDown": _big5_csv(header, rows)})
        tools = register_module_tools(daily_market_report, client)
        result = tools["get_daily_options_market_report"](
            "TXO", "20250602", "20250630", contract_month="202507"
        )
        assert len(result) < MAX_CHARS, f"輸出 {len(result):,} 字元，未設上限"
        assert f"共 {ROWS} 筆" in result

    def test_institutional_by_futures_is_bounded(self):
        header = [
            "日期", "商品名稱", "身份別",
            "多方交易口數", "多方交易契約金額(千元)", "空方交易口數", "空方交易契約金額(千元)",
            "多空交易口數淨額", "多空交易契約金額淨額(千元)",
            "多方未平倉口數", "多方未平倉契約金額(千元)", "空方未平倉口數", "空方未平倉契約金額(千元)",
            "多空未平倉口數淨額", "多空未平倉契約金額淨額(千元)",
        ]
        rows = [["2025/04/01", "臺股期貨", "外資及陸資"] + [str(100000 + i)] * 12 for i in range(ROWS)]
        client = OfflineClient({"/cht/3/futContractsDateDown": _big5_csv(header, rows)})
        tools = register_module_tools(institutional_details, client)
        result = tools["get_institutional_traders_by_futures"]("", "20250401", "20250630")
        assert len(result) < MAX_CHARS, f"輸出 {len(result):,} 字元，未設上限"
        assert f"共 {ROWS} 筆" in result
