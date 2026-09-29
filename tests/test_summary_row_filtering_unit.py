"""彙總列與空殼佔位物件不會被當成一般資料列（不打網路）。

TWSE 的 BFIAUU / TWT93U / TWTASU 都在 data 陣列末尾附一列全市場加總
（「總計」/「合計」），欄位結構與明細列完全相同。原本三個工具都沒過濾，
筆數多算一筆，且清單中會出現一筆量值為全市場加總的假交易
（實測 20260827：鉅額交易顯示 40 筆，其中末列量 27,681,085 是 39 筆真實
成交的總和，為真實最大單筆 8,059,880 的 3.4 倍）。

MIS 則是對前綴錯誤或不存在的代號回傳佔位物件 {"c": "", "z": "-", ...}，
留著會讓筆數灌水，並讓「查無報價」的訊息永遠不可達。

上游「仍然附彙總列」屬於 interface 契約，由 tests/e2e/test_history_tier2_api.py 驗證。
"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
import tools.history.block_trades_detail as block_trades_detail
import tools.history.short_sale_lending as short_sale_lending
import tools.realtime.stock_info as stock_info

pytestmark = pytest.mark.offline

TRADING_DATE = "20250102"


def _ok(rows):
    return {"stat": "OK", "data": rows}


BFIAUU = _ok([
    ["2330", "台積電", "配對交易", "1,000.00", "1,000,000", "1,000,000,000"],
    ["2317", "鴻海", "配對交易", "200.00", "500,000", "100,000,000"],
    ["總計", "", "", "", "1,500,000", "1,100,000,000"],
])

TWT93U = _ok([
    ["2330", "台積電"] + ["100"] * 12 + [""],
    ["2317", "鴻海"] + ["200"] * 12 + [""],
    ["", "合計"] + ["300"] * 12 + [""],
])

TWTASU = _ok([
    ["2330   台積電", "1", "2", "3", "4"],
    ["2317   鴻海", "5", "6", "7", "8"],
    ["合計", "6", "8", "10", "12"],
])


@pytest.fixture
def history_tools():
    client = OfflineClient({
        "/block/BFIAUU": BFIAUU,
        "/marginTrading/TWT93U": TWT93U,
        "/afterTrading/TWTASU": TWTASU,
    })
    return {
        **register_module_tools(block_trades_detail, client),
        **register_module_tools(short_sale_lending, client),
    }


class TestToolsExcludeSummaryRow:
    def test_block_trades_excludes_summary(self, history_tools):
        result = history_tools["get_block_trades_detail"](TRADING_DATE)
        assert "總計" not in result, "輸出仍含彙總列「總計」"
        assert "共 2 筆" in result, f"筆數未扣除彙總列：{result.splitlines()[0]}"

    def test_lending_balance_excludes_summary(self, history_tools):
        result = history_tools["get_short_sale_lending_balance_history"](TRADING_DATE)
        assert "合計" not in result
        assert "共 2 筆" in result

    def test_lending_trades_excludes_summary(self, history_tools):
        result = history_tools["get_short_sale_lending_trades_history"](TRADING_DATE)
        assert "合計" not in result
        assert "共 2 筆" in result

    def test_lending_trades_summary_is_not_a_stock_code(self, history_tools):
        """「合計」曾被 split 當成股票代號，用它查詢應回查無而非命中."""
        result = history_tools["get_short_sale_lending_trades_history"](TRADING_DATE, stock_no="合計")
        assert result.startswith("查無"), f"「合計」仍被當成股票代號: {result[:100]!r}"


# MIS 對不存在（或前綴錯誤）的代號回傳的佔位物件
PLACEHOLDER = {"c": "", "n": None, "z": "-", "ex": ""}


def _quote(code, ex):
    return {"c": code, "n": f"名稱{code}", "z": "100.0", "y": "99.0", "ex": ex,
            "a": "100.5_101_", "b": "100_99.5_", "f": "1_2_", "g": "3_4_"}


def _mis(params, _data):
    """上市查詢只認得 2330；上櫃查詢只認得 6547；其餘一律回佔位物件."""
    known = {"tse_2330.tw": _quote("2330", "tse"), "otc_6547.tw": _quote("6547", "otc")}
    return {"msgArray": [known.get(ch, PLACEHOLDER) for ch in params["ex_ch"].split("|")]}


@pytest.fixture
def realtime_tools():
    return register_module_tools(stock_info, OfflineClient({"/getStockInfo.jsp": _mis}))


class TestRealtimeQuoteExcludesPlaceholders:
    def test_unknown_code_reports_no_data(self, realtime_tools):
        """不存在的代號應回「查無」，而非「共 N 支」加一列空殼."""
        result = realtime_tools["get_realtime_quote"](["9999"])
        assert result.startswith("查無"), f"預期查無資料，實際: {result[:120]!r}"

    def test_count_matches_real_quotes(self, realtime_tools):
        """一支上市加一支上櫃應為 2 支：上市查詢回的空殼不得計入."""
        result = realtime_tools["get_realtime_quote"](["2330", "6547"])
        assert "（共 2 支）" in result, f"筆數含空殼: {result.splitlines()[0]!r}"
        assert "? [" not in result, "輸出含代號為空的佔位列"
