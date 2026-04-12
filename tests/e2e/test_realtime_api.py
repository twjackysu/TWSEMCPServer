"""測試 mis.twse.com.tw 即時報價 API。"""

from utils.api_client import TWSEAPIClient

MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


class TestRealtimeQuoteAPI:
    """Tool get_realtime_quote 使用 msgArray 中的 c, n, z, o, h, l, y, v, t, ex 欄位。
    c 用於代號顯示與 OTC fallback 判斷，ex 用於上市/上櫃判斷，
    其餘欄位消失只會顯示 "-" 不會 crash。
    """

    def test_api_returns_msg_array_with_required_fields(self):
        """確認 API 可達且 tool 依賴的關鍵欄位存在。"""
        result = TWSEAPIClient.get_json(
            MIS_URL, params={"ex_ch": "tse_2330.tw", "json": 1, "delay": 0}
        )
        assert "msgArray" in result
        assert len(result["msgArray"]) > 0
        item = result["msgArray"][0]
        # c 用於代號比對, ex 用於上市/上櫃判斷
        assert "c" in item, f"欄位 'c' 不存在，現有: {sorted(item.keys())}"
        assert "ex" in item, f"欄位 'ex' 不存在，現有: {sorted(item.keys())}"
