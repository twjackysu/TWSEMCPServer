"""上市相關工具的單元測試（不打網路）。

/company/newlisting 與 /company/applylistingLocal 的上市日期在 ApprovedListingDate（股票上市買賣日期），
ListingDate 是證期局核准上市契約日期；applylistingLocal 的前九個欄位整排錯一格。
上游欄位語意與錯位樣式由 tests/contract/test_listing_api.py 驗證。
"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
from tools.company import listing

pytestmark = pytest.mark.offline

NEW_LISTING = [
    {"Code": "6467", "Company": "泰合", "ApplicationDate": "1150327", "ApprovedDate": "1150519",
     "ListingDate": "", "ApprovedListingDate": "1151020"},
    {"Code": "2443", "Company": "利碟", "ApplicationDate": "", "ApprovedDate": "",
     "ListingDate": "", "ApprovedListingDate": ""},
]

# 2026-10-21 實際收到的錯位列（8908 欣雄）：Code 是序號、Company 是代號、ApplicationDate 是名稱…
SHIFTED_LOCAL = {
    "Code": "6", "Company": "8908", "ApplicationDate": "欣雄", "Chairman": "1150727",
    "AmountofCapital ": "朱文煌", "CommitteeDate": "3153327", "ApprovedDate": "", "AgreementDate": "1150915",
    "ListingDate": "1150924", "ApprovedListingDate": "1151016", "Underwriter": "第一金",
    "UnderwritingPrice": "", "Note": "櫃轉市",
}
ALIGNED_LOCAL = {
    "Code": "7909", "Company": "鈺祥", "ApplicationDate": "1151006", "Chairman": "莊士杰",
    "AmountofCapital ": "705927", "CommitteeDate": "", "ApprovedDate": "", "AgreementDate": "",
    "ListingDate": "", "ApprovedListingDate": "", "Underwriter": "凱基", "UnderwritingPrice": "", "Note": "",
}
FOREIGN = [{"No": "1", "Code": "4178", "Company": "永笙-KY", "ApplicationDate": "1141030",
            "ApprovedDate": "1150120", "ListingDate": "1150430"}]


def _tools(routes):
    return register_module_tools(listing, OfflineClient(routes))


def test_recently_listed_shows_the_first_trading_day_not_the_contract_approval():
    text = _tools({"/company/newlisting": NEW_LISTING})["get_recently_listed_companies"]()
    assert "- 泰合 (6467): 上市日期 2026-10-20" in text
    assert "- 利碟 (2443): 上市日期 —" in text


def test_shifted_local_application_row_is_put_back_under_its_keys():
    fixed = listing.normalize_local_application(SHIFTED_LOCAL)
    assert (fixed["Code"], fixed["Company"], fixed["ApplicationDate"], fixed["Chairman"]) == (
        "8908", "欣雄", "1150727", "朱文煌")
    assert (fixed["CommitteeDate"], fixed["ApprovedDate"], fixed["AgreementDate"]) == ("", "1150915", "1150924")
    assert fixed["ListingDate"] == "" and fixed["ApprovedListingDate"] == "1151016"
    assert fixed["Underwriter"] == "第一金" and fixed["Note"] == "櫃轉市"
    assert SHIFTED_LOCAL["Code"] == "6", "原始資料列不可被改動"


def test_aligned_local_application_row_passes_through():
    assert listing.normalize_local_application(ALIGNED_LOCAL) == ALIGNED_LOCAL


def test_local_applications_tool_formats_and_filters_by_the_repaired_name():
    fn = _tools({"/company/applylistingLocal": [SHIFTED_LOCAL, ALIGNED_LOCAL]})["get_local_companies_applying_for_listing"]
    text = fn()
    assert "- 欣雄 (8908): 申請日期 2026-07-27, 董事會通過上市 2026-09-15, 上市日期 2026-10-16" in text
    assert "- 鈺祥 (7909): 申請日期 2026-10-06, 董事會通過上市 —, 上市日期 —" in text
    filtered = fn(name="欣雄")
    assert "共有 1 筆" in filtered and "8908" in filtered


def test_foreign_applications_listing_date_is_listingdate():
    text = _tools({"/company/applylistingForeign": FOREIGN})["get_foreign_companies_applying_for_listing"]()
    assert "- 永笙-KY (4178): 申請日期 2025-10-30, 董事會通過上市 2026-01-20, 上市日期 2026-04-30" in text
