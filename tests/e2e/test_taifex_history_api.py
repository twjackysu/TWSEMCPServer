"""測試 www.taifex.com.tw 期交所歷史資料下載端點（Big5 CSV，非 openapi.taifex.com.tw）。
只驗證 tool 依欄位「順序」（index）存取時，欄位順序未被期交所調整。
"""

import csv
import io

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _post_csv(url: str, data: dict) -> list:
    resp = requests.post(url, headers=HEADERS, data=data, verify=False, timeout=20)
    text = resp.content.decode("big5", errors="replace")
    return list(csv.reader(io.StringIO(text)))


class TestFuturesDailyHistoryAPI:
    """Tool get_futures_daily_history 依 index 存取的欄位順序：
    0=交易日期 1=契約 2=到期月份(週別) 3=開盤價 4=最高價 5=最低價 6=收盤價
    7=漲跌價 8=漲跌% 9=成交量 10=結算價 11=未沖銷契約數 ... 17=交易時段
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/futDataDown",
            {
                "down_type": "1",
                "commodity_id": "TX",
                "commodity_id2": "",
                "queryStartDate": "2026/07/01",
                "queryEndDate": "2026/07/03",
            },
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "交易日期", "契約", "到期月份(週別)", "開盤價", "最高價", "最低價", "收盤價",
            "漲跌價", "漲跌%", "成交量", "結算價", "未沖銷契約數",
        ]
        assert header[:len(expected)] == expected, f"欄位順序異動: {header}"
        assert header[17] == "交易時段", f"交易時段欄位位置異動: {header}"


class TestInstitutionalTradersByFuturesHistoryAPI:
    """Tool get_institutional_traders_by_futures_history 依 index 存取的欄位順序：
    0=日期 1=商品名稱 2=身份別 3=多方交易口數 4=多方交易契約金額(千元)
    5=空方交易口數 6=空方交易契約金額(千元) 7=多空交易口數淨額 8=多空交易契約金額淨額(千元)
    9=多方未平倉口數 10=多方未平倉契約金額(千元) 11=空方未平倉口數 12=空方未平倉契約金額(千元)
    13=多空未平倉口數淨額 14=多空未平倉契約金額淨額(千元)
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/futContractsDateDown",
            {
                "queryStartDate": "2026/06/01",
                "queryEndDate": "2026/06/03",
                "commodityId": "TXF",
            },
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "日期", "商品名稱", "身份別",
            "多方交易口數", "多方交易契約金額(千元)", "空方交易口數", "空方交易契約金額(千元)",
            "多空交易口數淨額", "多空交易契約金額淨額(千元)",
            "多方未平倉口數", "多方未平倉契約金額(千元)", "空方未平倉口數", "空方未平倉契約金額(千元)",
            "多空未平倉口數淨額", "多空未平倉契約金額淨額(千元)",
        ]
        assert header == expected, f"欄位順序異動: {header}"
