"""
測試彙總列與空殼佔位物件不會被當成一般資料列。

TWSE 的 BFIAUU / TWT93U / TWTASU 都在 data 陣列末尾附一列全市場加總
（「總計」/「合計」），欄位結構與明細列完全相同。原本三個工具都沒過濾，
筆數多算一筆，且清單中會出現一筆量值為全市場加總的假交易
（實測 20260827：鉅額交易顯示 40 筆，其中末列量 27,681,085 是 39 筆真實
成交的總和，為真實最大單筆 8,059,880 的 3.4 倍）。

MIS 則是對前綴錯誤或不存在的代號回傳佔位物件 {"c": "", "z": "-", ...}，
留著會讓筆數灌水，並讓「查無報價」的訊息永遠不可達。
"""

import pytest

from utils.api_client import TWSEAPIClient
from utils.constants import SUMMARY_ROW_LABELS
from tests.helpers import fetch_or_skip, register_module_tools
import tools.history.block_trades_detail as block_trades_detail
import tools.history.short_sale_lending as short_sale_lending
import tools.realtime.stock_info as stock_info

TRADING_DATE = "20250102"


@pytest.fixture(scope="module")
def client():
    return TWSEAPIClient()


class TestUpstreamStillAppendsSummaryRow:
    """先確認上游仍然附彙總列——若哪天不附了，下面的過濾就成了無效程式碼."""

    def test_bfiauu_last_row_is_summary(self):
        resp = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/block/BFIAUU",
            params={"response": "json", "date": TRADING_DATE},
        )
        assert resp["data"][-1][0].strip() in SUMMARY_ROW_LABELS

    def test_twt93u_last_row_is_summary(self):
        resp = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U",
            params={"response": "json", "date": TRADING_DATE, "selectType": "ALL"},
        )
        assert resp["data"][-1][1].strip() in SUMMARY_ROW_LABELS

    def test_twtasu_last_row_is_summary(self):
        resp = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/afterTrading/TWTASU",
            params={"response": "json", "date": TRADING_DATE},
        )
        assert resp["data"][-1][0].split(None, 1)[0] in SUMMARY_ROW_LABELS


class TestToolsExcludeSummaryRow:
    def test_block_trades_excludes_summary(self, client):
        tools = register_module_tools(block_trades_detail, client)
        result = tools["get_block_trades_detail"](TRADING_DATE, limit=1000)
        for label in SUMMARY_ROW_LABELS:
            assert label not in result, f"輸出仍含彙總列「{label}」"

    def test_block_trades_count_excludes_summary(self, client):
        """筆數要少於 API 原始列數，且不能把彙總列算進去."""
        resp = fetch_or_skip(
            "https://www.twse.com.tw/rwd/zh/block/BFIAUU",
            params={"response": "json", "date": TRADING_DATE},
        )
        raw_rows = len(resp["data"])
        tools = register_module_tools(block_trades_detail, client)
        result = tools["get_block_trades_detail"](TRADING_DATE)
        assert f"共 {raw_rows - 1} 筆" in result, (
            f"筆數未扣除彙總列（API {raw_rows} 列）：{result.splitlines()[0]}"
        )

    def test_lending_balance_excludes_summary(self, client):
        tools = register_module_tools(short_sale_lending, client)
        result = tools["get_short_sale_lending_balance_history"](TRADING_DATE, limit=2000)
        assert "合計" not in result

    def test_lending_trades_excludes_summary(self, client):
        tools = register_module_tools(short_sale_lending, client)
        result = tools["get_short_sale_lending_trades_history"](TRADING_DATE, limit=2000)
        assert "合計" not in result

    def test_lending_trades_summary_is_not_a_stock_code(self, client):
        """「合計」曾被 split 當成股票代號，用它查詢應回查無而非命中."""
        tools = register_module_tools(short_sale_lending, client)
        result = tools["get_short_sale_lending_trades_history"](TRADING_DATE, stock_no="合計")
        assert result.startswith("查無"), f"「合計」仍被當成股票代號: {result[:100]!r}"


class TestRealtimeQuoteExcludesPlaceholders:
    def test_unknown_code_reports_no_data(self, client):
        """不存在的代號應回「查無」，而非「共 N 支」加一列空殼."""
        tools = register_module_tools(stock_info, client)
        result = tools["get_realtime_quote"](["9999"])
        assert result.startswith("查無"), f"預期查無資料，實際: {result[:120]!r}"

    def test_count_matches_real_quotes(self, client):
        """一支上市加一支上櫃應為 2 支：上市查詢回的空殼不得計入."""
        tools = register_module_tools(stock_info, client)
        result = tools["get_realtime_quote"](["2330", "6547"])
        assert "（共 2 支）" in result, f"筆數含空殼: {result.splitlines()[0]!r}"
        assert "? [" not in result, "輸出含代號為空的佔位列"
