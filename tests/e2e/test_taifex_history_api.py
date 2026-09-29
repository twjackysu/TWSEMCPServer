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


class TestPutCallRatioHistoryAPI:
    """Tool get_put_call_ratio_history 依 index 存取的欄位順序：
    0=日期 1=賣權成交量 2=買權成交量 3=買賣權成交量比率% 4=賣權未平倉量 5=買權未平倉量 6=買賣權未平倉量比率%
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/pcRatioDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/05"},
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "日期", "賣權成交量", "買權成交量", "買賣權成交量比率%",
            "賣權未平倉量", "買權未平倉量", "買賣權未平倉量比率%",
        ]
        assert header[:len(expected)] == expected, f"欄位順序異動: {header}"


class TestOptionsInstitutionalCallsPutsHistoryAPI:
    """Tool get_options_institutional_calls_puts_history 依 index 存取的欄位順序：
    0=日期 1=商品名稱 2=買賣權別 3=身份別 4=買方交易口數 5=買方交易契約金額(千元)
    6=賣方交易口數 7=賣方交易契約金額(千元) 8=交易口數買賣淨額 9=交易契約金額買賣淨額(千元)
    10=買方未平倉口數 12=賣方未平倉口數 14=未平倉口數買賣淨額
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/callsAndPutsDateDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/03", "commodityId": "TXO"},
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "日期", "商品名稱", "買賣權別", "身份別",
            "買方交易口數", "買方交易契約金額(千元)", "賣方交易口數", "賣方交易契約金額(千元)",
            "交易口數買賣淨額", "交易契約金額買賣淨額(千元)",
            "買方未平倉口數", "買方未平倉契約金額(千元)", "賣方未平倉口數", "賣方未平倉契約金額(千元)",
            "未平倉口數買賣淨額", "未平倉契約金額買賣淨額(千元)",
        ]
        assert header == expected, f"欄位順序異動: {header}"


class TestLargeTradersFuturesHistoryAPI:
    """Tool get_large_traders_futures_history 依 index 存取的欄位順序：
    0=日期 1=商品(契約)（篩選契約用） 3=到期月份(週別) 4=交易人類別
    5=前五大交易人買方 6=前五大交易人賣方 7=前十大交易人買方 8=前十大交易人賣方 9=全市場未沖銷部位數
    此端點無伺服器端契約篩選，tool 於本地端以 row[1] 過濾。
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/largeTraderFutDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/02"},
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "日期", "商品(契約)", "商品名稱(契約名稱)", "到期月份(週別)", "交易人類別",
            "前五大交易人買方", "前五大交易人賣方", "前十大交易人買方", "前十大交易人賣方",
            "全市場未沖銷部位數",
        ]
        assert header == expected, f"欄位順序異動: {header}"

    def test_no_server_side_contract_filter(self):
        """確認此端點忽略任何契約篩選參數，回傳全部商品（tool 依賴此行為才會在本地端過濾）。"""
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/largeTraderFutDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/01", "contractId": "TX"},
        )
        codes = set(r[1].strip() for r in rows[1:] if len(r) > 1)
        assert len(codes) > 1, "端點行為可能已變更為支援伺服器端契約篩選，tool 邏輯需重新檢視"


class TestOptionsDailyHistoryAPI:
    """Tool get_options_daily_history 依 index 存取的欄位順序：
    0=交易日期 1=契約 2=到期月份(週別) 3=履約價 4=買賣權 5=開盤價 6=最高價 7=最低價 8=收盤價
    9=成交量 10=結算價 11=未沖銷契約數 ... 17=交易時段
    注意：header 列尾端多一個逗號（欄位數比實際資料列多 1），tool 的共用 decode_and_parse_csv()
    容忍此落差；此測試僅比對已知欄位前綴，不比對完整長度。
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/optDataDown",
            {
                "down_type": "1",
                "commodity_id": "TXO",
                "commodity_id2": "",
                "queryStartDate": "2026/06/01",
                "queryEndDate": "2026/06/01",
            },
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "交易日期", "契約", "到期月份(週別)", "履約價", "買賣權",
            "開盤價", "最高價", "最低價", "收盤價", "成交量", "結算價", "未沖銷契約數",
        ]
        assert header[:len(expected)] == expected, f"欄位順序異動: {header}"
        assert header[17] == "交易時段", f"交易時段欄位位置異動: {header}"

    def test_commodity_id_filters_server_side(self):
        """確認 commodity_id 參數真的在伺服器端篩選（與 largeTraderFutDown 行為不同）。"""
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/optDataDown",
            {
                "down_type": "1",
                "commodity_id": "TXO",
                "commodity_id2": "",
                "queryStartDate": "2026/06/01",
                "queryEndDate": "2026/06/01",
            },
        )
        contracts = set(r[1].strip() for r in rows[1:] if r and len(r) > 1)
        assert contracts == {"TXO"}, f"commodity_id 篩選行為可能已變更: {contracts}"


class TestInstitutionalTotalHistoryAPI:
    """Tool get_institutional_total_history 依 index 存取的欄位順序：
    0=日期 1=身份別 2=多方交易口數 3=多方交易契約金額(百萬元) 4=空方交易口數
    5=空方交易契約金額(百萬元) 6=多空交易口數淨額 7=多空交易契約金額淨額(百萬元)
    8=多方未平倉口數 10=空方未平倉口數 12=多空未平倉口數淨額
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/totalTableDateDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/03"},
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        expected = [
            "日期", "身份別",
            "多方交易口數", "多方交易契約金額(百萬元)", "空方交易口數", "空方交易契約金額(百萬元)",
            "多空交易口數淨額", "多空交易契約金額淨額(百萬元)",
            "多方未平倉口數", "多方未平倉契約金額(百萬元)", "空方未平倉口數", "空方未平倉契約金額(百萬元)",
            "多空未平倉口數淨額", "多空未平倉契約金額淨額(百萬元)",
        ]
        assert header == expected, f"欄位順序異動: {header}"


class TestOptionsInstitutionalByContractHistoryAPI:
    """Tool get_options_institutional_by_contract_history 依 index 存取的欄位順序：
    0=日期 1=商品名稱 2=身份別 3=多方交易口數 5=空方交易口數 7=多空交易口數淨額
    9=多方未平倉口數 11=空方未平倉口數 13=多空未平倉口數淨額
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/optContractsDateDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/03", "commodityId": "TXO"},
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


class TestInstitutionalFutOptSplitHistoryAPI:
    """Tool get_institutional_fut_opt_split_history 依 index 存取的欄位（期貨=偶數index、選擇權=奇數index）：
    0=日期 1=身份別 2/3=多方交易口數(期貨/選擇權) 6/7=空方交易口數 10/11=多空交易口數淨額
    14/15=多方未平倉口數 18/19=空方未平倉口數 22/23=多空未平倉口數淨額
    """

    def test_hardcoded_column_order(self):
        rows = _post_csv(
            "https://www.taifex.com.tw/cht/3/futAndOptDateDown",
            {"queryStartDate": "2026/06/01", "queryEndDate": "2026/06/03"},
        )
        assert len(rows) > 1, "查無資料，無法驗證欄位順序"
        header = rows[0]
        assert len(header) == 26, f"欄位數不為 26，header 結構可能已變更: {header}"
        assert header[0] == "日期" and header[1] == "身份別", f"前兩欄異動: {header[:2]}"
        assert "期貨" in header[2] and "選擇權" in header[3], f"欄位2/3應為期貨/選擇權多方交易口數: {header[2:4]}"
        assert "期貨" in header[22] and "選擇權" in header[23], f"欄位22/23應為期貨/選擇權多空未平倉口數淨額: {header[22:24]}"
