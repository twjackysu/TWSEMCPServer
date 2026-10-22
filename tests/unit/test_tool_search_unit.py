"""Clients that defer the tool list find tools by searching it: the descriptions must hold the words people use.

The server's main client (Anthropic Messages API + MCP connector) loads tools on demand with Anthropic's regex
tool search (`tool_search_tool_regex_20251119`): a Python `re.search`, case-insensitive, over each tool's name,
description, argument names and argument descriptions, returning the first 5 (or the model's `limit`, usually
10) matches **in catalog order**, unranked — measured 2026-10-22: a live search returned exactly the tools/list
order. So a tool is found when its text holds the word searched for, and is not crowded out by tools listed
before it. This module simulates that search offline (不打網路).
"""

import asyncio
import re

import pytest
from fastmcp import FastMCP

import tools
from tests.offline import OfflineClient

pytestmark = pytest.mark.offline

# The words people use for each tool's data (Chinese and English). Each must appear in that tool's searchable
# text; a space also matches "_" or "-", as models write `block.?trade` for names like get_block_trades_detail.
# When users ask for a tool in words it lacks, add them to its description and here.
WORDS = {
    "get_realtime_quote": ["即時", "報價", "盤中", "股價", "quote", "realtime"],
    "get_stock_history": ["日K", "K線", "歷史股價", "開盤", "收盤", "成交量", "OHLC", "history"],
    "get_otc_stock_history": ["日K", "K線", "上櫃", "歷史股價", "history"],
    "get_stock_daily_trading": ["收盤行情", "全市場", "漲跌", "成交量"],
    "get_otc_daily": ["上櫃", "收盤行情", "OTC"],
    "get_adjusted_price_history": ["還原權息", "還原股價", "adjusted", "除權息"],
    "get_technical_indicators": ["KD", "RSI", "MACD", "均線", "布林", "technical"],
    "get_stock_screener": ["選股", "篩選", "本益比", "殖利率", "淨值比", "screener"],
    "get_industry_peers": ["同業", "同產業", "比較", "peer"],
    "get_twse_institutional_investors_summary": ["三大法人", "外資", "投信", "自營商", "買賣超", "排行", "institutional"],
    "get_twse_institutional_investors_by_stock": ["三大法人", "外資", "投信", "自營商", "個股", "institutional"],
    "get_otc_institutional": ["三大法人", "上櫃", "外資", "投信", "買賣超", "institutional"],
    "get_market_institutional_amounts_history": ["三大法人", "買賣金額", "外資", "institutional"],
    "get_margin_balance": ["融資", "融券", "資券", "信用交易", "margin"],
    "get_otc_margin_balance": ["融資", "融券", "上櫃", "margin"],
    "get_stock_valuation_ratios": ["本益比", "殖利率", "淨值比", "P/E", "PER", "PBR", "valuation"],
    "get_otc_valuation": ["本益比", "殖利率", "淨值比", "上櫃", "valuation"],
    "get_company_monthly_revenue": ["月營收", "營收", "年增率", "月增率", "revenue", "YoY"],
    "get_company_income_statement": ["損益表", "EPS", "每股盈餘", "毛利", "營業收入", "淨利", "income"],
    "get_company_balance_sheet": ["資產負債表", "資產", "負債", "股東權益", "balance"],
    "get_company_cash_flow_statement": ["現金流量", "自由現金流", "cash flow"],
    "get_company_dividend": ["股利", "配息", "現金股利", "股票股利", "dividend"],
    "get_dividend_rights_schedule": ["除權息", "除息", "除權", "現金股利"],
    "get_exright_results_history": ["除權息", "參考價", "除息", "填息"],
    "get_company_major_news": ["重大訊息", "公告", "news"],
    "get_investor_conferences": ["法說會", "法人說明會", "investor conference"],
    "get_company_board_shareholdings": ["董監", "持股", "質押", "設質"],
    "get_company_insider_holding_changes": ["內部人", "持股", "insider"],
    "get_treasury_stock_buybacks": ["庫藏股", "買回", "buyback"],
    "get_shareholding_distribution": ["集保", "股權分散", "大戶", "散戶", "籌碼", "shareholding"],
    "get_etf_holdings": ["成分股", "持股", "前十大", "holdings", "constituent"],
    "get_etf_daily_nav": ["折溢價", "淨值", "NAV", "ETF", "premium"],
    "get_etf_monthly_stats": ["規模", "受益人", "申購", "買回", "ETF"],
    "get_etf_info": ["ETF", "基本資料", "配息", "追蹤指數"],
    "get_put_call_ratio": ["Put/Call", "PCR", "賣買權比", "選擇權", "多空"],
    "get_futures_institutional": ["期貨", "三大法人", "未平倉", "外資", "futures"],
    "get_large_traders_futures_oi": ["大額交易人", "期貨", "未沖銷", "large trader"],
    "get_daily_futures_market_report": ["期貨", "行情", "台指期", "futures"],
    "get_futures_intraday": ["盤中", "分K", "分鐘", "走勢", "intraday"],
    "get_daily_options_market_report": ["選擇權", "行情", "履約價", "options"],
    "get_business_cycle_indicators": ["景氣燈號", "景氣對策信號", "領先指標", "business cycle"],
    "get_taiwan_pmi": ["PMI", "採購經理人", "NMI"],
    "get_exchange_rates": ["匯率", "新台幣", "美元", "USD", "exchange rate"],
    "get_taiex_index_history": ["加權指數", "大盤", "TAIEX", "指數"],
    "get_market_index_info": ["指數", "類股", "index"],
    "get_market_turnover_history": ["成交量", "成交金額", "成交值", "量能", "turnover"],
    "get_foreign_holdings": ["外資持股", "持股比率", "foreign"],
    "get_short_sale_lending_balance_history": ["借券", "融券", "餘額", "short"],
    "get_block_trades_detail": ["鉅額交易", "block trade"],
    "get_daily_day_trading_targets": ["當沖", "當日沖銷", "day trading"],
    "get_market_disposal_stocks": ["處置股", "處置", "disposal"],
    "get_today_notice_stocks": ["注意股", "注意", "notice"],
    "get_market_holiday_schedule": ["休市", "假日", "holiday"],
    "get_company_profile": ["基本資料", "公司資料", "產業別", "profile"],
}

# (question, a pattern a model writes for it, tools that answer it). The first block was written the way
# models wrote them in live runs (2026-10-22); "(live)" ones are verbatim. Each must reach a right tool within
# the first 10 matches, the limit models usually pass.
SEARCHES = [
    ("台積電三大法人(live)", "三大法人|institutional|法人", {"get_twse_institutional_investors_by_stock", "get_twse_institutional_investors_summary"}),
    ("外資買超(live)", "外資|三大法人|institutional|foreign", {"get_twse_institutional_investors_summary"}),
    ("上櫃本益比最低(live)", "本益比|PE|ratio|上櫃|otc|排行|screen|rank", {"get_stock_screener", "get_otc_valuation"}),
    ("Put/Call Ratio(live)", "put.?call|Put/Call|選擇權", {"get_put_call_ratio"}),
    ("0050 成分股(live)", "ETF.*成分|成分股|constituent|holding", {"get_etf_holdings"}),
    ("景氣燈號(live)", "景氣|燈號|business.?cycle|indicator", {"get_business_cycle_indicators"}),
    ("KD RSI(live)", "KD|RSI|技術|technical|indicator", {"get_technical_indicators"}),
    ("月營收(live)", "月營收|revenue|monthly", {"get_company_monthly_revenue"}),
    ("0050 成分股", "成分股|持股", {"get_etf_holdings"}),
    ("上櫃三大法人", "上櫃.*法人|otc.*institutional", {"get_otc_institutional", "get_otc_institutional_summary"}),
    ("三大法人買賣金額", "三大法人.*金額|買賣金額|institutional.*amount", {"get_market_institutional_amounts_history", "get_otc_institutional_summary"}),
    ("融資融券", "融資|融券|margin", {"get_margin_balance", "get_otc_margin_balance"}),
    ("個股本益比", "本益比|殖利率|淨值比|valuation|P/E", {"get_stock_valuation_ratios", "get_otc_valuation"}),
    ("高殖利率選股", "選股|篩選|screen", {"get_stock_screener"}),
    ("同業比較", "同業|peer|同產業", {"get_industry_peers"}),
    ("還原股價", "還原|adjusted", {"get_adjusted_price_history"}),
    ("歷史股價", "日K|K線|歷史股價|stock.?history", {"get_stock_history", "get_otc_stock_history"}),
    ("即時報價", "即時|報價|realtime|quote", {"get_realtime_quote"}),
    ("EPS", "損益|income.?statement|EPS|每股盈餘", {"get_company_income_statement"}),
    ("資產負債表", "資產負債|balance.?sheet", {"get_company_balance_sheet"}),
    ("自由現金流", "現金流|cash.?flow", {"get_company_cash_flow_statement"}),
    ("股利", "股利|配息|dividend", {"get_company_dividend"}),
    ("除權息", "除權息|除息|ex.?dividend|ex.?right", {"get_dividend_rights_schedule", "get_exright_results_history", "get_otc_exright"}),
    ("重大訊息", "重大訊息|major.?news|material", {"get_company_major_news"}),
    ("法說會", "法說會|法人說明會|investor.?conference", {"get_investor_conferences"}),
    ("董監質押", "董監|質押|設質|board|pledge", {"get_company_board_shareholdings"}),
    ("內部人", "內部人|insider", {"get_company_insider_holding_changes"}),
    ("庫藏股", "庫藏股|treasury|buyback", {"get_treasury_stock_buybacks"}),
    ("集保大戶", "集保|股權分散|大戶|散戶|shareholding.?distribution", {"get_shareholding_distribution"}),
    ("處置股", "處置|disposal", {"get_market_disposal_stocks", "get_otc_disposal_stocks"}),
    ("注意股", "注意股|警示|warning|notice", {"get_today_notice_stocks", "get_otc_warning_stocks"}),
    ("當沖", "當沖|當日沖銷|day.?trading", {"get_daily_day_trading_targets"}),
    ("ETF 折溢價", "折溢價|淨值|NAV|premium", {"get_etf_daily_nav"}),
    ("ETF 規模", "規模|受益人|申購|買回", {"get_etf_monthly_stats"}),
    ("PCR", "PCR|賣買權比", {"get_put_call_ratio"}),
    ("期貨三大法人", "期貨.*法人|futures.*institutional", {"get_futures_institutional", "get_institutional_traders_by_futures"}),
    ("大額交易人", "大額交易人|large.?trader", {"get_large_traders_futures_oi", "get_large_traders_options_oi"}),
    ("台指期行情", "台指期|期貨.*行情|futures.*market", {"get_daily_futures_market_report"}),
    ("期貨分K", "盤中|分K|分鐘|intraday|minute", {"get_futures_intraday"}),
    ("選擇權行情", "選擇權.*行情|option.*market|履約價", {"get_daily_options_market_report"}),
    ("領先指標", "領先指標|景氣|business.?cycle", {"get_business_cycle_indicators"}),
    ("PMI", "PMI|採購經理", {"get_taiwan_pmi"}),
    ("匯率", "匯率|exchange.?rate|新台幣", {"get_exchange_rates"}),
    ("加權指數", "加權指數|大盤|TAIEX", {"get_taiex_index_history", "get_market_index_info"}),
    ("成交量值", "成交量|成交金額|成交值|turnover|量能", {"get_market_turnover_history"}),
    ("外資持股比率", "外資持股|foreign.*holding", {"get_foreign_holdings", "get_otc_foreign_holdings"}),
    ("借券", "借券|lending|short.?sale", {"get_short_sale_lending_balance_history", "get_short_sale_lending_trades_history"}),
    ("鉅額交易", "鉅額|block.?trade", {"get_block_trades_detail", "get_block_trades_daily"}),
    ("休市日", "休市|假日|holiday", {"get_market_holiday_schedule"}),
    ("公司基本資料", "公司資料|基本資料|company.?profile", {"get_company_profile"}),
]


@pytest.fixture(scope="module")
def catalog():
    """(tool name, searchable text) in tools/list order."""
    mcp = FastMCP("probe")
    tools.register_all_tools(mcp, OfflineClient({}))
    out = []
    for tool in asyncio.run(mcp.list_tools()):
        parts = [tool.name, tool.description or ""]
        for name, prop in (tool.parameters or {}).get("properties", {}).items():
            parts += [name, prop.get("description", "")]
        out.append((tool.name, " ".join(parts)))
    return out


def _search(catalog, pattern):
    rx = re.compile(pattern, re.IGNORECASE)
    return [name for name, text in catalog if rx.search(text)]


def test_every_tool_named_here_exists(catalog):
    names = {name for name, _ in catalog}
    assert set(WORDS) - names == set()
    assert {t for _, _, expected in SEARCHES for t in expected} - names == set()


def test_the_words_people_use_are_in_the_tool_s_text(catalog):
    texts = dict(catalog)
    missing = {tool: [w for w in words
                      if not re.search(re.escape(w).replace(r"\ ", "[ _-]?"), texts[tool], re.IGNORECASE)]
               for tool, words in WORDS.items()}
    assert {tool: words for tool, words in missing.items() if words} == {}


@pytest.mark.parametrize("question, pattern, expected", SEARCHES, ids=[s[0] for s in SEARCHES])
def test_a_search_finds_the_tool_within_the_first_ten(catalog, question, pattern, expected):
    found = _search(catalog, pattern)
    rank = next((i + 1 for i, name in enumerate(found) if name in expected), None)
    assert rank is not None and rank <= 10, f"{question}: /{pattern}/ → rank {rank}; first 10: {found[:10]}"


def test_openapi_pass_through_tools_are_listed_last():
    """They are more than half the catalog and broadly worded; listed first they crowd the search results."""
    modules = tools.discover_tool_modules()
    flags = [any(m == p or m.startswith(p + ".") for p in tools.OPENAPI_PACKAGES) for m in modules]
    assert flags == sorted(flags) and any(flags) and not all(flags)
