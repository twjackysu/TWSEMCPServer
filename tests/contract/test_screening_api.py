"""Contract tests for utils/market_snapshot.py (get_stock_screener / get_industry_peers)."""

from tests.helpers import fetch_or_skip, records_or_skip
from utils.api_client import TWSEAPIClient
from utils.market_snapshot import (
    BWIBBU_D_URL,
    LISTED_PROFILE_ENDPOINT,
    MI_INDEX_URL,
    TPEX_PE_URL,
    TPEX_PROFILE_URL,
    TPEX_QUOTES_URL,
)

FIXED_DATE = "20250103"


def test_industry_codes_share_one_system_across_markets():
    """上市 t187ap03_L 的「產業別」與上櫃 mopsfin_t187ap03_O 的 SecuritiesIndustryCode 必須是同一套兩位數代碼
    （台積電與環球晶都是 24），同業比較才能跨市場合併."""
    listed = records_or_skip(TWSEAPIClient.get_instance().fetch_data(LISTED_PROFILE_ENDPOINT), LISTED_PROFILE_ENDPOINT)
    tsmc = next(r for r in listed if r.get("公司代號") == "2330")
    otc = records_or_skip(fetch_or_skip(TPEX_PROFILE_URL), "mopsfin_t187ap03_O")
    gw = next((r for r in otc if str(r.get("SecuritiesCompanyCode", "")).strip() == "6488"), None)
    assert gw is not None, "mopsfin_t187ap03_O 找不到 6488，代號欄位可能已變更"
    assert tsmc.get("產業別") == "24" and str(gw.get("SecuritiesIndustryCode")).strip() == "24", (
        f"產業代碼體系已變更：2330={tsmc.get('產業別')!r}，6488={gw.get('SecuritiesIndustryCode')!r}"
    )


def test_industry_member_lists_carry_names():
    listed = fetch_or_skip(MI_INDEX_URL, params={"response": "json", "type": "24", "date": FIXED_DATE})
    titles = [t.get("title") or "" for t in listed.get("tables") or []]
    member_table = next((t for t in listed.get("tables") or [] if "每日收盤行情(半導體業)" in (t.get("title") or "")), None)
    assert member_table and any(r[0] == "2330" for r in member_table.get("data") or []), f"產業成員表已變更: {titles}"
    otc = fetch_or_skip(TPEX_QUOTES_URL, params={"response": "json", "type": "24", "date": "2025/01/03"})
    table = (otc.get("tables") or [{}])[0]
    assert table.get("category") and any(r[0] == "6488" for r in table.get("data") or []), "上櫃產業成員表已變更"


def test_valuation_dates_can_drive_quote_requests():
    """snapshot 先取估值資料日，再用該日查行情，避免把兩個交易日的價格與本益比混在一起."""
    val = fetch_or_skip(BWIBBU_D_URL, params={"response": "json", "selectType": "ALL"})
    assert len(str(val.get("date", ""))) == 8, f"BWIBBU_d 不再回傳資料日: {val.get('date')!r}"
    pe = fetch_or_skip(TPEX_PE_URL, params={"response": "json"})
    assert len(str(pe.get("date", ""))) == 8, f"peQryDate 不再回傳資料日: {pe.get('date')!r}"
