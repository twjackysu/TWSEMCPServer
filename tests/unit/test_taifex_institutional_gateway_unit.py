"""sources/taifex/institutional.py、large_traders.py、put_call_ratio.py 與其工具的單元測試（不打網路）。

假資料的標題與資料列取自期交所真實下載（2025-01-03、2026-10-21 等）；上游真實格式由
tests/contract/test_taifex_history_api.py 驗證。
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from sources.taifex.institutional import (
    calls_puts_positions,
    futures_contract_positions,
    institutional_split,
    institutional_totals,
    option_contract_positions,
)
from sources.taifex.large_traders import futures_large_traders, option_large_traders
from sources.taifex.put_call_ratio import put_call_ratios
from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.taifex import (
    futures_position,
    institutional_details,
    institutional_general,
    large_traders_oi,
    put_call_ratio,
)
from utils import plain
from utils.errors import UpstreamFormatError

pytestmark = pytest.mark.offline

TOTAL_HEADER = ["日期", "身份別", "多方交易口數", "多方交易契約金額(百萬元)", "空方交易口數", "空方交易契約金額(百萬元)",
                "多空交易口數淨額", "多空交易契約金額淨額(百萬元)", "多方未平倉口數", "多方未平倉契約金額(百萬元)",
                "空方未平倉口數", "空方未平倉契約金額(百萬元)", "多空未平倉口數淨額", "多空未平倉契約金額淨額(百萬元)"]
TOTAL_ROWS = [["2025/01/03", "自營商", "244752", "113749", "211021", "118421", "33731", "-4672", "162138", "48628",
               "370395", "123052", "-208257", "-74424"]]

SPLIT_HEADER = ["日期", "身份別"] + [
    f"{market}{name}"
    for name in ("多方交易口數", "多方交易契約金額(千元)", "空方交易口數", "空方交易契約金額(千元)", "多空交易口數淨額",
                 "多空交易契約金額淨額(千元)", "多方未平倉口數", "多方未平倉契約金額(千元)", "空方未平倉口數",
                 "空方未平倉契約金額(千元)", "多空未平倉口數淨額", "多空未平倉契約金額淨額(千元)")
    for market in ("期貨", "選擇權")]
SPLIT_ROWS = [["2025/01/03", "自營商", "87824", "156928", "113089417", "659177", "76957", "134064", "117845599",
               "575314", "10867", "22864", "-4756182", "83863.0", "81109", "81029", "47876896", "751109", "292731",
               "77664", "122329023", "723223", "-211622", "3365", "-74452127", "27886"]]

CONTRACTS_HEADER = ["日期", "商品名稱", "身份別", "多方交易口數", "多方交易契約金額(千元)", "空方交易口數",
                    "空方交易契約金額(千元)", "多空交易口數淨額", "多空交易契約金額淨額(千元)", "多方未平倉口數",
                    "多方未平倉契約金額(千元)", "空方未平倉口數", "空方未平倉契約金額(千元)", "多空未平倉口數淨額",
                    "多空未平倉契約金額淨額(千元)"]
CONTRACTS_ROWS = [["2026/10/21", "臺股期貨", "外資及陸資", "54619", "512637727", "53557", "502794263", "1062",
                   "9843464", "9410", "88480368", "95482", "897846647", "-86072", "-809366279"]]

CALLS_PUTS_HEADER = ["日期", "商品名稱", "買賣權別", "身份別", "買方交易口數", "買方交易契約金額(千元)", "賣方交易口數",
                     "賣方交易契約金額(千元)", "交易口數買賣淨額", "交易契約金額買賣淨額(千元)", "買方未平倉口數",
                     "買方未平倉契約金額(千元)", "賣方未平倉口數", "賣方未平倉契約金額(千元)", "未平倉口數買賣淨額",
                     "未平倉契約金額買賣淨額(千元)"]
CALLS_PUTS_ROWS = [
    ["2025/01/03", "臺指選擇權", "CALL", "自營商", "84606", "347150", "66829", "291546", "17777", "55603", "51104",
     "517521", "34009", "261439", "17095", "256082"],
    ["2025/01/03", "臺指選擇權", "PUT", "自營商", "66249", "277866", "71337", "306359", "-5088", "-28493", "38641",
     "409954", "25529", "185809", "13112", "224145"],
]

LT_HEADER = ["日期", "商品(契約)", "商品名稱(契約名稱)", "到期月份(週別)", "交易人類別", "前五大交易人買方",
             "前五大交易人賣方", "前十大交易人買方", "前十大交易人賣方", "全市場未沖銷部位數"]
LT_ROWS = [["2025/01/03", "TX     ", "臺股期貨(TX+MTX/4+TMF/20)           ", "999999  ", "0", "28962", "34725",
            "38873", "48543", "85490"]]
LT_OPT_HEADER = LT_HEADER[:3] + ["買賣權"] + LT_HEADER[3:]
LT_OPT_ROWS = [["2025/01/03", "TXO    ", "臺指", "賣權", "999999  ", "1", "39138", "0", "56161", "0", "343759"]]

PCR_HEADER = ["日期", "賣權成交量", "買權成交量", "買賣權成交量比率%", "賣權未平倉量", "買權未平倉量", "買賣權未平倉量比率%"]
PCR_ROWS = [["2021/01/04", "409683", "362995", "112.86", "291020", "209950", "138.61", ""]]  # rows end with an empty cell


def csv(header, rows) -> bytes:
    return ("\r\n".join(",".join(r) for r in [header] + rows) + "\r\n").encode("cp950")


def _client(path, body):
    return OfflineClient({f"/cht/3/{path}": body})


DAY = datetime(2025, 1, 3)


def test_total_table_rows_become_typed_positions():
    (row,) = institutional_totals(_client("totalTableDateDown", csv(TOTAL_HEADER, TOTAL_ROWS)), DAY, DAY)
    p = row.positions
    assert (row.day, row.identity) == (date(2025, 1, 3), "自營商")
    assert (p.long_volume, p.short_volume, p.net_volume, p.net_value) == (244752, 211021, 33731, Decimal("-4672"))
    assert (p.long_oi, p.long_oi_value, p.short_oi, p.short_oi_value, p.net_oi, p.net_oi_value) == (
        162138, Decimal("48628"), 370395, Decimal("123052"), -208257, Decimal("-74424"))


def test_split_rows_keep_futures_and_options_apart():
    (row,) = institutional_split(_client("futAndOptDateDown", csv(SPLIT_HEADER, SPLIT_ROWS)), DAY, DAY)
    assert (row.futures.long_volume, row.futures.net_value, row.futures.net_oi_value) == (
        87824, Decimal("-4756182"), Decimal("-74452127"))
    assert (row.options.long_volume, row.options.net_value, row.options.net_oi) == (156928, Decimal("83863.0"), 3365)


def test_contract_code_is_posted_and_calls_puts_are_told_apart():
    forms = []

    def route(header, rows):
        def answer(_params, form):
            forms.append(dict(form))
            return csv(header, rows)
        return answer

    client = OfflineClient({"/cht/3/futContractsDateDown": route(CONTRACTS_HEADER, CONTRACTS_ROWS),
                            "/cht/3/optContractsDateDown": route(CONTRACTS_HEADER, CONTRACTS_ROWS),
                            "/cht/3/callsAndPutsDateDown": route(CALLS_PUTS_HEADER, CALLS_PUTS_ROWS)})
    (fut,) = futures_contract_positions(client, DAY, DAY, "TXF")
    assert (fut.contract, fut.identity, fut.call_put, fut.positions.net_oi_value) == (
        "臺股期貨", "外資及陸資", "", Decimal("-809366279"))
    option_contract_positions(client, DAY, DAY)
    call, put = calls_puts_positions(client, DAY, DAY, "TXO")
    assert (call.call_put, put.call_put, put.positions.net_volume, put.positions.short_oi) == ("CALL", "PUT", -5088, 25529)
    assert forms == [{"queryStartDate": "2025/01/03", "queryEndDate": "2025/01/03", "commodityId": code}
                     for code in ("TXF", "", "TXO")]


def test_large_trader_rows_are_stripped_and_typed():
    (fut,) = futures_large_traders(_client("largeTraderFutDown", csv(LT_HEADER, LT_ROWS)), DAY, DAY)
    assert (fut.contract, fut.name, fut.month, fut.trader_type, fut.call_put) == (
        "TX", "臺股期貨(TX+MTX/4+TMF/20)", "999999", "0", "")
    assert (fut.top5_buy, fut.top5_sell, fut.top10_buy, fut.top10_sell, fut.market_oi) == (28962, 34725, 38873, 48543, 85490)
    (opt,) = option_large_traders(_client("largeTraderOptDown", csv(LT_OPT_HEADER, LT_OPT_ROWS)), DAY, DAY)
    assert (opt.contract, opt.call_put, opt.trader_type, opt.top5_sell, opt.market_oi) == ("TXO", "賣權", "1", 0, 343759)


def test_put_call_ratio_rows_are_typed():
    (day,) = put_call_ratios(_client("pcRatioDown", csv(PCR_HEADER, PCR_ROWS)), DAY, DAY)
    assert (day.day, day.put_volume, day.call_volume, day.volume_ratio) == (date(2021, 1, 4), 409683, 362995, Decimal("112.86"))
    assert (day.put_oi, day.call_oi, day.oi_ratio) == (291020, 209950, Decimal("138.61"))


def test_columns_are_found_by_name():
    # 日期 stays first: decode_and_parse_csv drops rows whose first cell is blank
    order = [0] + list(range(1, len(TOTAL_HEADER)))[::-1]
    swapped = csv([TOTAL_HEADER[i] for i in order], [[r[i] for i in order] for r in TOTAL_ROWS])
    assert institutional_totals(_client("totalTableDateDown", swapped), DAY, DAY) == institutional_totals(
        _client("totalTableDateDown", csv(TOTAL_HEADER, TOTAL_ROWS)), DAY, DAY)


def test_renamed_column_html_and_short_rows():
    renamed = csv(["日期", "身份別", "多方交易口數", "多方交易契約金額(千元)"] + TOTAL_HEADER[4:], TOTAL_ROWS)
    with pytest.raises(UpstreamFormatError, match=r"多方交易契約金額\(百萬元\)"):
        institutional_totals(_client("totalTableDateDown", renamed), DAY, DAY)
    # decode_and_parse_csv lets a row one cell short of the header through (some headers end with a comma)
    with pytest.raises(UpstreamFormatError, match="只有 6 欄"):
        put_call_ratios(_client("pcRatioDown", csv(PCR_HEADER, [PCR_ROWS[0][:6]])), DAY, DAY)
    html = b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">\r\n<head></head>\r\n'
    assert option_large_traders(_client("largeTraderOptDown", html), DAY, DAY) is None


# ---------- 工具輸出：與改用 gateway 之前逐字相同 ----------

def test_plain_prints_the_published_digits():
    assert [plain(v) for v in (Decimal("83863.0"), Decimal("0.00000000"), Decimal("-4672"), 62488, None)] == [
        "83863.0", "0.00000000", "-4672", "62488", "-"]


def test_split_tool_prints_the_same_lines_as_before():
    tools = register_module_tools(futures_position, _client("futAndOptDateDown", csv(SPLIT_HEADER, SPLIT_ROWS)))
    assert ("2025/01/03 | 自營商\n"
            "  期貨: 交易 多87824/空76957/淨10867（淨額 -4756182 千元）| 未平倉 多81109/空292731/淨-211622（淨額 -74452127 千元）\n"
            "  選擇權: 交易 多156928/空134064/淨22864（淨額 83863.0 千元）| 未平倉 多81029/空77664/淨3365（淨額 27886 千元）"
            ) in tools["get_futures_institutional"]("20250103")


def test_total_table_tool_prints_the_same_lines_as_before():
    tools = register_module_tools(institutional_general, _client("totalTableDateDown", csv(TOTAL_HEADER, TOTAL_ROWS)))
    assert ("2025/01/03 | 自營商\n"
            "  交易量: 多 244752 / 空 211021 / 淨 33731\n"
            "  交易金額(百萬): 多 113749 / 空 118421 / 淨 -4672\n"
            "  未平倉口數: 多 162138 / 空 370395 / 淨 -208257\n"
            "  未平倉契約價值(百萬): 多 48628 / 空 123052 / 淨 -74424") in tools["get_institutional_general"]("20250103")


def test_calls_puts_tool_prints_the_same_lines_as_before():
    tools = register_module_tools(institutional_details, _client("callsAndPutsDateDown", csv(CALLS_PUTS_HEADER, CALLS_PUTS_ROWS)))
    text = tools["get_institutional_traders_calls_puts"]("TXO", "CALL", "20250103")
    assert ("▶ 2025/01/03 臺指選擇權 CALL\n"
            "  自營商\n"
            "    交易量: 買方 84606 / 賣方 66829 / 淨 17777\n"
            "    交易金額(千元): 買方 347150 / 賣方 291546 / 淨 55603\n"
            "    未平倉口數: 買方 51104 / 賣方 34009 / 淨 17095\n"
            "    未平倉契約價值(千元): 買方 517521 / 賣方 261439 / 淨 256082") in text
    assert "PUT" not in text


def test_large_traders_tools_print_the_same_lines_as_before():
    fut = register_module_tools(large_traders_oi, _client("largeTraderFutDown", csv(LT_HEADER, LT_ROWS)))
    assert ("【期貨大額交易人未沖銷部位】TX（臺股期貨(TX+MTX/4+TMF/20)）| 20250103（共 1 筆）\n\n"
            "2025/01/03 | 所有月份總計 | 所有交易人 | 前五大: 多 28962 / 空 34725 | 前十大: 多 38873 / 空 48543 | "
            "市場總未平倉: 85490") in fut["get_large_traders_futures_oi"]("TX", "20250103")
    opt = register_module_tools(large_traders_oi, _client("largeTraderOptDown", csv(LT_OPT_HEADER, LT_OPT_ROWS)))
    assert ("2025/01/03 | 賣權 | 所有月份總計 | 特定法人 | 前五大: 多 39138 / 空 0 | 前十大: 多 56161 / 空 0 | "
            "市場總未平倉: 343759") in opt["get_large_traders_options_oi"]("TXO", "", "20250103")


def test_put_call_ratio_tool_prints_the_same_line_as_before():
    tools = register_module_tools(put_call_ratio, _client("pcRatioDown", csv(PCR_HEADER, PCR_ROWS)))
    assert ("2021/01/04 | 成交量 PCR:112.86%（Put:409683 Call:362995） | 未平倉 PCR:138.61%（Put:291020 Call:209950）"
            ) in tools["get_put_call_ratio"]("20210104")
