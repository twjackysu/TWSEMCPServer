"""參數驗證交給 FastMCP：列舉參數是 Literal、範圍是 Field(ge=, le=)，錯誤值在進到工具之前就被擋下，
並由 toolkit.validation.ArgumentErrorsInChinese 以中文說明（不打網路：驗證失敗不會呼叫工具本體）。

工具函式不再自己檢查這些值，所以這裡透過真正的 server（server.mcp）呼叫，而不是直接呼叫函式。
"""

import asyncio
from typing import get_args

import pydantic
import pytest
from fastmcp import Client
from pydantic import TypeAdapter

import server
from toolkit import RequiredTradingDate, TradingDate
from toolkit.params import DATE_PATTERN
from tools.analytics import screening
from tools.company import financials
from tools.etf import daily_nav, monthly_stats
from tools.history import exright_day_trading_indices
from tools.macro import ndc_indicators
from tools.mops import dividend, investor_conference, major_news, treasury_guarantees
from tools.otc import institutional_summary
from tools.taifex import intraday, trading_statistics
from utils import institutional

pytestmark = pytest.mark.offline


def _call(name, args):
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, args, raise_on_error=False)
    return asyncio.run(run())


def _tools():
    async def run():
        async with Client(server.mcp) as client:
            return await client.list_tools()
    return asyncio.run(run())


@pytest.mark.parametrize("tool,args,message", [
    ("get_twse_institutional_investors_summary", {"side": "up"}, "side 只能是 abs、buy、sell（收到 'up'）"),
    ("get_twse_institutional_investors_summary", {"sort_by": "volume"},
     "sort_by 只能是 total、foreign、trust、dealer（收到 'volume'）"),
    ("get_otc_institutional", {"side": "both"}, "side 只能是 abs、buy、sell"),
    ("get_market_institutional_amounts_history", {"period": "year"}, "period 只能是 day、week、month（收到 'year'）"),
    ("get_otc_institutional_summary", {"scope": "otc"}, "scope 只能是 stocks、all"),
    ("get_etf_daily_nav", {"sort_by": "volume"}, "sort_by 只能是 scale、premium、discount、creation、redemption"),
    ("get_etf_daily_nav", {"limit": 0}, "limit 不可小於 1（收到 0）"),
    ("get_etf_daily_nav", {"limit": 101}, "limit 不可大於 100（收到 101）"),
    ("get_etf_monthly_stats", {"code": "0050", "months": 25}, "months 不可大於 24（收到 25）"),
    ("get_etf_monthly_stats", {"sort_by": "nav"}, "sort_by 只能是 scale、holders、net_flow、regular"),
    ("get_stock_screener", {"market": "us"}, "market 只能是 all、listed、otc"),
    ("get_stock_screener", {"sort_by": "roe"}, "sort_by 只能是 yield、pe、pb、change、volume"),
    ("get_industry_peers", {"code": "2330", "sort_by": "roe"}, "sort_by 只能是 yield、pe、pb、change、volume"),
    ("get_business_cycle_indicators", {"table": "gdp"}, "table 只能是 signal、signal_components、leading、coincident、lagging"),
    ("get_business_cycle_indicators", {"months": 61}, "months 不可大於 60（收到 61）"),
    ("get_taiwan_pmi", {"months": 0}, "months 不可小於 1（收到 0）"),
    ("get_foreign_holdings", {"sort_by": "name"}, "sort_by 只能是 code、ratio"),
    ("get_market_index_info", {"category": "tech"}, "category 只能是 major、sector、esg、leverage、return、thematic、dividend、all"),
    ("get_monthly_trading_statistics", {"market": "stock"}, "market 只能是 futures、options"),
    ("get_futures_intraday", {"interval": 3}, "interval 只能是 1、5、15、30、60（收到 3）"),
    ("get_futures_intraday", {"session": "morning"}, "session 只能是 day、night、all"),
    ("get_company_dividend", {"code": "2330", "year_type": "x"}, "year_type 只能是 dividend、board"),
    ("get_investor_conferences", {"year": "2026", "market": "nyse"}, "market 只能是 sii、otc、rotc、pub"),
    ("get_treasury_stock_buybacks", {"market": "nyse"}, "market 只能是 sii、otc、rotc、pub"),
    ("get_company_major_news", {"market": "nyse"}, "market 只能是 （留空）、sii、otc、rotc、pub（收到 'nyse'）"),
    ("get_shareholding_distribution", {"code": "2330", "weeks": 14}, "weeks 不可大於 13（收到 14）"),
    ("get_shareholding_distribution", {"code": "2330", "weeks": 0}, "weeks 不可小於 1（收到 0）"),
    ("get_company_profitability_analysis_summary", {"order_by": "本益比"}, "order_by 只能是 公司代號、公司名稱"),
    ("get_company_profitability_analysis_summary", {"limit": 101}, "limit 不可大於 100（收到 101）"),
    ("get_stock_valuation_ratios", {"offset": -1}, "offset 不可小於 0（收到 -1）"),
    ("get_stock_valuation_ratios", {"limit": "many"}, "limit 必須是整數（收到 'many'）"),
    ("get_stock_valuation_ratios", {"bogus": 1}, "沒有 bogus 這個參數"),
    ("get_shareholding_distribution", {"weeks": 2}, "缺少必填參數 code"),
    # 日期一律是西元 YYYYMMDD（toolkit.TradingDate）；轉成民國或 TPEx 格式是各工具的事
    ("get_stock_history", {"stock_no": "2330", "date": "2026-09"},
     "date 日期格式錯誤，請使用西元 YYYYMMDD，例如 \"20260930\"（收到 '2026-09'）"),
    ("get_stock_history", {"stock_no": "2330", "date": ""}, "date 日期格式錯誤"),  # 必填：不可留空
    ("get_otc_margin_balance", {"date": "20261301"}, "date 日期不存在（收到 '20261301'）"),
    ("get_exright_results_history", {"start_date": "2026-07-01", "end_date": "20260731"}, "start_date 日期格式錯誤"),
    ("get_otc_valuation", {"date": "2026-09-29"}, "date 日期格式錯誤"),
    ("get_treasury_stock_buybacks", {"start_date": "2026-09-01"}, "start_date 日期格式錯誤"),
    ("get_daily_futures_market_report", {"start_date": "2026/06/01"}, "start_date 日期格式錯誤"),
    ("get_stock_valuation_ratios", {"date": "2026-09-30"}, "date 日期格式錯誤"),  # 以前會原樣送給證交所
    ("get_twse_news", {"start_date": "1151001"}, "start_date 日期格式錯誤"),  # 民國 7 碼不接受
    ("get_twse_institutional_investors_summary", {"date": "20260230"}, "date 日期不存在"),
])
def test_rejected_before_the_tool_runs_with_a_chinese_message(tool, args, message):
    result = _call(tool, args)
    assert result.is_error, f"{tool}({args}) 應被拒絕"
    text = result.content[0].text
    assert message in text, text
    assert "validation error" not in text and "Input should" not in text, f"英文的 pydantic 訊息沒被換掉: {text}"


def test_several_errors_are_reported_together():
    text = _call("get_twse_institutional_investors_summary", {"side": "up", "limit": 0}).content[0].text
    assert "side 只能是" in text and "limit 不可小於 1" in text and "；" in text


def test_every_limit_and_offset_parameter_is_bounded_in_the_schema():
    """分頁參數的範圍寫在 schema 裡，client 呼叫前就看得到；新工具忘了用 Limit / Offset 會在這裡失敗。"""
    unbounded = []
    for tool in _tools():
        props = tool.input_schema.get("properties", {})
        if "limit" in props and props["limit"].get("minimum") != 1:
            unbounded.append(f"{tool.name}.limit")
        if "offset" in props and props["offset"].get("minimum") != 0:
            unbounded.append(f"{tool.name}.offset")
    assert not unbounded, unbounded


def test_every_date_parameter_is_a_trading_date():
    """日期參數都用 TradingDate / RequiredTradingDate，格式寫在 schema 裡；新工具忘了用會在這裡失敗。"""
    wrong = []
    for tool in _tools():
        required = set(tool.input_schema.get("required", []))
        for name, prop in tool.input_schema.get("properties", {}).items():
            if name in ("date", "start_date", "end_date"):
                expected = DATE_PATTERN if name in required else r"^(\d{8})?$"
                if prop.get("pattern") != expected:
                    wrong.append(f"{tool.name}.{name}: {prop.get('pattern')!r}")
    assert not wrong, wrong


@pytest.mark.parametrize("value,ok", [
    ("", True), ("20260930", True), ("20240229", True),
    ("20250229", False), ("20261301", False), ("2026-09-30", False), ("1150930", False), (" 20260930", False),
])
def test_trading_date_accepts_gregorian_days_that_exist(value, ok):
    adapter = TypeAdapter(TradingDate)
    if ok:
        assert adapter.validate_python(value) == value  # 原樣交給工具
    else:
        with pytest.raises(pydantic.ValidationError):
            adapter.validate_python(value)
    with pytest.raises(pydantic.ValidationError):
        TypeAdapter(RequiredTradingDate).validate_python("")


def test_enumerations_reach_the_schema():
    props = {t.name: t.input_schema["properties"] for t in _tools()}
    assert props["get_twse_institutional_investors_summary"]["side"]["enum"] == ["abs", "buy", "sell"]
    assert props["get_futures_intraday"]["interval"]["enum"] == [1, 5, 15, 30, 60]
    assert (props["get_shareholding_distribution"]["weeks"]["minimum"],
            props["get_shareholding_distribution"]["weeks"]["maximum"]) == (1, 13)


@pytest.mark.parametrize("alias,accepted", [
    (institutional.Investor, institutional.SORT_LABELS),
    (institutional.Side, institutional.SIDES),
    (institutional.Period, institutional.PERIODS),
    (institutional_summary.Scope, institutional_summary.SCOPES),
    (daily_nav.SortBy, daily_nav.SORTS),
    (monthly_stats.SortBy, monthly_stats.SORTS),
    (screening.Market, screening.MARKETS),
    (screening.SortBy, screening.SORTS),
    (ndc_indicators.Table, ndc_indicators.CYCLE_TABLES),
    (exright_day_trading_indices.IndexCategory, exright_day_trading_indices.INDEX_CATEGORIES),
    (trading_statistics.Market, trading_statistics._MONTHLY_STATS_URLS),
    (intraday.Session, intraday.SESSIONS),
    (dividend.YearType, dividend.YEAR_TYPES),
    (investor_conference.Market, investor_conference.MARKETS),
    (treasury_guarantees.Market, treasury_guarantees.MARKETS),
    (major_news.Market, {"": None, **major_news.MARKET_LABELS}),
    (financials.ProfitabilitySort,
     set(financials.PROFITABILITY_SORT_FIELDS) | set(financials.PROFITABILITY_SORT_FIELDS.values())),
], ids=lambda v: getattr(v, "__name__", None) if not isinstance(v, (dict, set)) else "")
def test_each_enumeration_matches_the_mapping_it_indexes(alias, accepted):
    """Literal 的值與程式裡查表用的 dict 一致：多一個值會 KeyError，少一個值則有功能用不到。"""
    assert set(get_args(alias)) == set(accepted)
