"""Contract tests for the listing endpoints whose field names do not say what they hold.

- /company/newlisting: ApprovedListingDate is the listing date (股票上市買賣日期), ListingDate is
  not. Checked against the newest listed stock's first trading day in STOCK_DAY.
- /company/applylistingLocal: rows come shifted against their keys; tools/company/listing.py
  repairs them. Every row must be either shifted the known way or aligned, nothing else.
"""

import re

from tests.helpers import fetch_or_skip, records_or_skip
from tools.company.listing import normalize_local_application
from utils import TWSEAPIClient

ROC_DATE = re.compile(r"^\d{7}$")
STOCK_CODE = re.compile(r"^[0-9A-Z]{4,6}$")


def test_newlisting_approved_listing_date_is_the_first_trading_day():
    rows = records_or_skip(TWSEAPIClient.get_data("/company/newlisting"), "/company/newlisting")
    dated = [r for r in rows if ROC_DATE.match(str(r.get("ApprovedListingDate", "")))]
    assert dated, "沒有任何一筆帶 7 碼民國日期的 ApprovedListingDate"
    newest = max(dated, key=lambda r: r["ApprovedListingDate"])
    roc = newest["ApprovedListingDate"]
    resp = fetch_or_skip("https://www.twse.com.tw/exchangeReport/STOCK_DAY", params={
        "response": "json", "stockNo": newest["Code"], "date": f"{int(roc[:3]) + 1911}{roc[3:5]}01"})
    first = (resp.get("data") or [[None]])[0][0]
    assert first == f"{roc[:3]}/{roc[3:5]}/{roc[5:]}", (
        f"{newest['Code']} 的 ApprovedListingDate {roc} 不是當月第一個交易日 {first}：上市日期欄位的意義可能變了")


def test_applylisting_local_rows_are_shifted_or_aligned():
    rows = records_or_skip(TWSEAPIClient.get_data("/company/applylistingLocal"), "/company/applylistingLocal")
    for raw in rows:
        row = normalize_local_application(raw)
        assert STOCK_CODE.match(str(row.get("Code", ""))), f"代號欄不是股票代號：{raw}"
        assert any(not ch.isdigit() for ch in str(row.get("Company", ""))), f"名稱欄不是公司名稱：{raw}"
        for key in ("ApplicationDate", "ApprovedDate", "ApprovedListingDate"):
            value = str(row.get(key, ""))
            assert value == "" or ROC_DATE.match(value), f"{key} 不是民國日期：{raw}"
