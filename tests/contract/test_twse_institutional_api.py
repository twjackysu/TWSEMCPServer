"""
測試 twse.com.tw/rwd/zh/fund/T86 三大法人買賣超 API。
透過 sources/twse/t86.py 驗證三種欄位格式都還讀得出來，以及 selectType 的篩選。
"""

from sources.twse.t86 import t86_flows
from tests.helpers import gateway_or_skip

FIXED_DATE = "20250103"  # 固定歷史交易日，確保資料穩定
FIXED_STOCK = "2330"     # 台積電，流動性高必有法人進出


class TestT86Gateway:
    """get_twse_institutional_investors_summary / get_twse_institutional_investors_by_stock 只透過
    sources/twse/t86.py 讀 T86；gateway 依欄名取值，欄位改名、列寬不符或格子不是股數都會丟 UpstreamFormatError。"""

    def test_fixed_day_parses_current_layout(self):
        day = gateway_or_skip(t86_flows, "ALL", FIXED_DATE)
        assert day is not None and day.date == FIXED_DATE and day.flows, "固定歷史交易日應有資料"
        tsmc = next((f for f in day.flows if f.code == FIXED_STOCK), None)
        assert tsmc is not None and tsmc.name == "台積電", f"{FIXED_DATE} 找不到 {FIXED_STOCK}"

    def test_older_layouts_still_parse(self):
        """2017-10-03 的 16 欄（外資未拆）與 2014-10-03 的 12 欄（自營商也未拆）格式都要讀得出來。"""
        for date in ("20171003", "20141003"):
            day = gateway_or_skip(t86_flows, "24", date)
            assert day is not None and day.flows, f"{date} 應有資料"


class TestT86SelectType:
    """get_twse_institutional_investors_summary 的 category 直接對應 selectType：預設 ALLBUT0999（不含權證），
    etf＝0099P，產業代碼原樣傳入；category="stock" 從 ALLBUT0999 去掉 00 開頭代號，依賴「ETF 皆為 00 開頭」."""

    @staticmethod
    def _codes(select_type: str) -> set:
        day = gateway_or_skip(t86_flows, select_type, FIXED_DATE)
        assert day is not None, f"selectType={select_type} 不再被接受"
        return {f.code for f in day.flows}

    def test_select_types_filter(self):
        everything, no_warrants = self._codes("ALL"), self._codes("ALLBUT0999")
        assert no_warrants < everything, "ALLBUT0999 不再是 ALL 的子集（排除權證的篩選失效）"  # contract-ok: 代號集合的子集，工具依賴 selectType 篩選
        semiconductor = self._codes("24")
        assert semiconductor and semiconductor < no_warrants, "產業代碼 selectType 不再篩選"  # contract-ok: 同上，產業代碼篩選

    def test_etf_codes_are_exactly_the_00_prefixed_rows(self):
        etf, no_warrants = self._codes("0099P"), self._codes("ALLBUT0999")
        assert etf and etf == {c for c in no_warrants if c.startswith("00")}, (
            "ETF 與 00 開頭代號不再一一對應，category=stock 的排除規則需要調整"
        )
