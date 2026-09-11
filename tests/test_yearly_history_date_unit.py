"""get_stock_yearly_history 送出的查詢日期不會凍結在某個年份（不打網路）。

FMNPTK 以 date 的年份當作歷年序列的終點。日期若寫死成某一年，跨年之後最新年度就會從
結果中默默消失：輸出格式一切正常，只是少了一列，呼叫端沒有任何線索可以察覺。
"""

from datetime import datetime

import pytest

from tests.helpers import register_module_tools
from tools.history import stock_monthly_yearly_history

# FMNPTK tables[0] 的 row 結構：年度,成交股數,成交金額,成交筆數,最高價,日期,最低價,日期,收盤平均價
YEARLY_ROWS = [
    ["113", "1,000", "2,000", "30", "600.00", "113/01/02", "500.00", "113/03/04", "550.00"],
    ["114", "1,100", "2,200", "33", "700.00", "114/01/02", "600.00", "114/03/04", "650.00"],
]


class _CapturingClient:
    """記下最後一次 fetch_json 的 params，並回一份 FMNPTK 形狀的固定資料."""

    def __init__(self):
        self.last_params = None

    def fetch_json(self, url, params=None, timeout=None, headers=None):
        self.last_params = params
        return {"stat": "OK", "tables": [{"data": YEARLY_ROWS}]}


@pytest.fixture
def client():
    return _CapturingClient()


@pytest.fixture
def get_stock_yearly_history(client):
    tools = register_module_tools(stock_monthly_yearly_history, client)
    return tools["get_stock_yearly_history"]


def test_query_date_is_today(get_stock_yearly_history, client):
    get_stock_yearly_history("2330")
    assert client.last_params["date"] == datetime.now().strftime("%Y%m%d")


def test_query_date_tracks_the_current_year(get_stock_yearly_history, client):
    """真正會壞掉的是年份：年份寫死時，跨年後最新一年不會出現在結果裡."""
    get_stock_yearly_history("2330")
    assert client.last_params["date"][:4] == str(datetime.now().year)


def test_rows_are_still_rendered(get_stock_yearly_history):
    """對照組：確認上面兩項不是因為工具整個查詢失敗才通過."""
    result = get_stock_yearly_history("2330")
    assert "共 2 年" in result
    assert "114年" in result
