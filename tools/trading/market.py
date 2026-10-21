"""Market trading tools for TWSE data."""

from typing import List, Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    MSG_NO_MATCHING_DATA,
    MSG_OFFSET_OUT_OF_RANGE,
    format_list_response,
    DEFAULT_DISPLAY_LIMIT,
)
from toolkit import ListToolSpec, create_list_tool, handle_api_errors


# Simple list tools that follow: fetch → optional name filter → paginate.
SIMPLE_LIST_TOOLS: List[ListToolSpec] = [
    ListToolSpec(
        endpoint="/exchangeReport/TWT88U", name="get_stocks_no_price_change_first_five_days",
        summary="查詢上市個股首五日無漲跌幅。",
        label="上市個股首五日無漲跌幅資料", empty_data_type="上市個股首五日無漲跌幅",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 承銷價 {i.get('PriceUnderwritten', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/Announcement/BFZFZU_T", name="get_financial_program_abnormal_recommendations",
        summary="查詢投資理財節目異常推介個股。",
        label="投資理財節目異常推介個股資料", empty_data_type="投資理財節目異常推介個股",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): {i.get('Number', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/TWTBAU1", name="get_suspended_day_trading_announcement",
        summary="查詢集中市場暫停先賣後買當日沖銷交易標的預告表。",
        label="集中市場暫停先賣後買當日沖銷交易標的預告表資料", empty_data_type="集中市場暫停先賣後買當日沖銷交易標的預告表",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 暫停日期 {i.get('StartDate', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/TWTBAU2", name="get_suspended_day_trading_history",
        summary="查詢集中市場暫停先賣後買當日沖銷交易歷史查詢。",
        label="集中市場暫停先賣後買當日沖銷交易歷史資料", empty_data_type="集中市場暫停先賣後買當日沖銷交易歷史",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 暫停日期 {i.get('StartDate', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/MI_INDEX4", name="get_cross_market_trading_info",
        summary="查詢每日上市上櫃跨市場成交資訊。",
        label="每日上市上櫃跨市場成交資訊", empty_data_type="每日上市上櫃跨市場成交資訊",
        formatter=lambda i: f"- {i.get('Date', 'N/A')}: 台灣指數 {i.get('FormosaIndex', 'N/A')} ({i.get('Change', 'N/A')}) 成交金額 {i.get('TradeValue', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/TWT53U", name="get_odd_lot_trading_quotes",
        summary="查詢集中市場零股交易行情單。",
        label="集中市場零股交易行情單資料", empty_data_type="集中市場零股交易行情單",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 成交價 {i.get('TradePrice', 'N/A')}, 成交量 {i.get('TradeVolume', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/TWTAWU", name="get_suspended_trading_stocks",
        summary="查詢集中市場暫停交易證券。",
        label="集中市場暫停交易證券資料", empty_data_type="集中市場暫停交易證券",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 停止 {i.get('TradingHaltDate', 'N/A')}, 恢復 {i.get('TradingResumptionDate', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/BFI84U", name="get_margin_loan_restrictions_announcement",
        summary="查詢集中市場停資停券預告表。",
        label="集中市場停資停券預告表資料", empty_data_type="集中市場停資停券預告表",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): {i.get('Reason', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/block/BFIAUU_d", name="get_block_trades_daily",
        summary="查詢集中市場鉅額交易日成交量值統計。",
        label="集中市場鉅額交易日成交量值統計資料", empty_data_type="集中市場鉅額交易日成交量值統計",
        formatter=lambda i: f"- {i.get('Date', 'N/A')}: 成交量 {i.get('TradeVolume', 'N/A')}, 總成交金額 {i.get('TradeValue', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/block/BFIAUU_m", name="get_block_trades_monthly",
        summary="查詢集中市場鉅額交易月成交量值統計。",
        label="集中市場鉅額交易月成交量值統計資料", empty_data_type="集中市場鉅額交易月成交量值統計",
        formatter=lambda i: f"- {i.get('Month', 'N/A')}: 成交量 {i.get('TradeVolume', 'N/A')}, 總成交金額 {i.get('TradeValue', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/block/BFIAUU_y", name="get_block_trades_yearly",
        summary="查詢集中市場鉅額交易年成交量值統計。",
        label="集中市場鉅額交易年成交量值統計資料", empty_data_type="集中市場鉅額交易年成交量值統計",
        formatter=lambda i: f"- {i.get('Month', 'N/A')}: 成交量 {i.get('TradeVolume', 'N/A')}, 總成交金額 {i.get('TradeValue', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/STOCK_FIRST", name="get_first_listed_foreign_stocks_daily",
        summary="查詢每日第一上市外國股票成交量值。",
        label="每日第一上市外國股票成交量值資料", empty_data_type="每日第一上市外國股票成交量值",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 成交量 {i.get('TradeVolume', 'N/A')}, 成交金額 {i.get('TradeValue', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/TWT85U", name="get_securities_trading_changes",
        summary="查詢集中市場證券變更交易。",
        label="集中市場證券變更交易資料", empty_data_type="集中市場證券變更交易",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): {i.get('PeriodicCallAuctionTrading', 'N/A')}\n",
    ),
    ListToolSpec(
        endpoint="/exchangeReport/TWT84U", name="get_stock_price_changes",
        summary="查詢上市個股股價升降幅度。",
        label="上市個股股價升降幅度資料", empty_data_type="上市個股股價升降幅度",
        filter_field="Name", name_hint="股票名稱關鍵字（選填）",
        formatter=lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): 漲停 {i.get('TodayLimitUp', 'N/A')}, 跌停 {i.get('TodayLimitDown', 'N/A')}\n",
    ),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market trading tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    for spec in SIMPLE_LIST_TOOLS:
        create_list_tool(mcp, spec, client)

    # --- Tools with custom headers, branching, or multi-section output ---

    @mcp.tool
    @handle_api_errors()
    def get_top_20_volume_stocks(name: str = "", limit: int = 20, offset: int = 0) -> str:
        """查詢集中市場每日成交量前二十名證券。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 20）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/MI_INDEX20")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場每日成交量前二十名證券")

        if name:
            data = [d for d in data if name in d.get("Name", "")]
            if not data:
                return MSG_NO_MATCHING_DATA.format(data_type="集中市場每日成交量前二十名證券")

        date = data[0].get("Date", "N/A") if data else "N/A"

        def formatter(item):
            rank = item.get("Rank", "N/A")
            code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            volume = item.get("TradeVolume", "N/A")
            transaction = item.get("Transaction", "N/A")
            closing_price = item.get("ClosingPrice", "N/A")
            direction = item.get("Dir", "")
            change = item.get("Change", "N/A")
            change_str = f"{direction}{change}" if direction and change != "N/A" else change
            return (
                f"{rank}. {stock_name} ({code})\n"
                f"   成交量: {volume} | 成交筆數: {transaction}\n"
                f"   收盤價: {closing_price} | 漲跌: {change_str}\n\n"
            )

        total = len(data)
        page_data = data[offset:offset + limit]
        if not page_data:
            return MSG_OFFSET_OUT_OF_RANGE.format(
                offset=offset, data_type="集中市場每日成交量前二十名證券資料", count=total
            )
        end = min(offset + limit, total)

        header = f"集中市場每日成交量前二十名證券 (日期: {date})（共 {total} 筆"
        if total > limit or offset > 0:
            header += f"，顯示第 {offset + 1}–{end} 筆"
        header += "）:\n\n"

        result = header
        for item in page_data:
            result += formatter(item)

        remaining = total - offset - limit
        if remaining > 0:
            result += f"... 還有 {remaining} 筆，使用 offset={offset + limit} 查看更多"

        return result.strip()

    @mcp.tool
    @handle_api_errors()
    def get_after_hours_trading(code: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢集中市場盤後定價交易。

        Args:
            code: 股票代號（選填，預設全部）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/BFT41U")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場盤後定價交易")

        if code:
            filtered = [item for item in data if item.get("Code") == code]
            if not filtered:
                return f"查無股票代碼 {code} 的盤後定價交易資料。"
            item = filtered[0]
            stock_name = item.get("Name", "N/A")
            trade_price = item.get("TradePrice", "N/A")
            trade_volume = item.get("TradeVolume", "N/A")
            trade_value = item.get("TradeValue", "N/A")
            transaction = item.get("Transaction", "N/A")
            bid_volume = item.get("BidVolume", "N/A")
            ask_volume = item.get("AskVolume", "N/A")
            result = f"{stock_name} ({code}) 盤後定價交易資訊：\n\n成交價: {trade_price}\n"
            if trade_volume and trade_volume != "":
                result += f"成交量: {trade_volume}\n成交金額: {trade_value}\n成交筆數: {transaction}\n"
            else:
                result += "狀態: 無成交\n"
            if bid_volume and bid_volume != "":
                result += f"委買量: {bid_volume}\n"
            if ask_volume and ask_volume != "":
                result += f"委賣量: {ask_volume}\n"
            return result

        traded_data = [item for item in data if item.get("TradeVolume") and item.get("TradeVolume") != ""]
        if not traded_data:
            return "目前沒有盤後定價交易成交資料。"

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            trade_price = item.get("TradePrice", "N/A")
            trade_volume = item.get("TradeVolume", "N/A")
            trade_value = item.get("TradeValue", "N/A")
            return f"- {stock_name} ({stock_code})\n  成交價: {trade_price} | 成交量: {trade_volume} | 成交金額: {trade_value}\n"

        return format_list_response(traded_data, "集中市場盤後定價交易資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_market_gain_loss_statistics() -> str:
        """查詢集中市場漲跌證券數統計表。

        回傳資訊包含類型、上漲、漲停、下跌、跌停、持平、未成交、無比價家數。
        """
        data = _client.fetch_data("/opendata/twtazu_od")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場漲跌證券數統計表")

        result = f"集中市場漲跌證券數統計表 (共 {len(data)} 筆):\n\n"
        for item in data:
            date = item.get("出表日期", "N/A")
            category = item.get("類型", "N/A")
            rising = item.get("上漲", "N/A")
            limit_up = item.get("漲停", "N/A")
            falling = item.get("下跌", "N/A")
            limit_down = item.get("跌停", "N/A")
            unchanged = item.get("持平", "N/A")
            no_trade = item.get("未成交", "N/A")
            no_comparison = item.get("無比價", "N/A")
            result += f"【{category}】 日期: {date}\n"
            result += f"  上漲: {rising} 家 (漲停: {limit_up})\n"
            result += f"  下跌: {falling} 家 (跌停: {limit_down})\n"
            result += f"  持平: {unchanged} 家\n"
            result += f"  未成交: {no_trade} 家\n"
            result += f"  無比價: {no_comparison} 家\n\n"
        return result.strip()

    @mcp.tool
    @handle_api_errors()
    def get_abnormal_accumulated_notice_stocks(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢集中市場公布注意累計次數異常資訊。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/announcement/notetrans")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場公布注意累計次數異常資訊")

        valid_data = [item for item in data if item.get("Code", "") != ""]
        if not valid_data:
            return MSG_NO_DATA.format(data_type="集中市場公布注意累計次數異常資訊")

        if name:
            valid_data = [d for d in valid_data if name in d.get("Name", "")]

        def formatter(item):
            code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            criteria = item.get("RecentlyMetAttentionSecuritiesCriteria", "N/A")
            return f"- {stock_name} ({code})\n  符合注意標準: {criteria}\n\n"

        return format_list_response(valid_data, "集中市場公布注意累計次數異常資訊", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_today_notice_stocks(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢集中市場當日公布注意股票。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/announcement/notice")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場當日公布注意股票")

        valid_data = [item for item in data if item.get("Code", "") != ""]
        if not valid_data:
            return MSG_NO_DATA.format(data_type="集中市場當日公布注意股票")

        if name:
            valid_data = [d for d in valid_data if name in d.get("Name", "")]

        def formatter(item):
            number = item.get("Number", "N/A")
            code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            announcement_count = item.get("NumberOfAnnouncement", "N/A")
            trading_info = item.get("TradingInfoForAttention", "N/A")
            date = item.get("Date", "N/A")
            closing_price = item.get("ClosingPrice", "N/A")
            pe_ratio = item.get("PE", "N/A")
            return (
                f"{number}. {stock_name} ({code})\n"
                f"   公布次數: {announcement_count} | 日期: {date}\n"
                f"   收盤價: {closing_price} | 本益比: {pe_ratio}\n"
                f"   注意事項: {trading_info}\n\n"
            )

        return format_list_response(valid_data, "集中市場當日公布注意股票資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_daily_securities_lending_volume(limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市上櫃股票當日可借券賣出股數。

        Args:
            limit: 回傳筆數上限（每市場各 limit 筆，預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/SBL/TWT96U")
        if not data:
            return MSG_NO_DATA.format(data_type="上市上櫃股票當日可借券賣出股數")

        twse_data = [item for item in data if item.get("TWSECode")]
        gretai_data = [item for item in data if item.get("GRETAICode")]

        total_twse = len(twse_data)
        total_gretai = len(gretai_data)
        # 兩個市場共用同一個 offset，所以要先切好頁再決定要印哪些區塊：只有「兩邊都翻過尾端」
        # 才是真的越界；只有一邊沒資料時，該區塊整段不印即可。
        page_twse = twse_data[offset:offset + limit]
        page_gretai = gretai_data[offset:offset + limit]
        if not page_twse and not page_gretai:
            return MSG_OFFSET_OUT_OF_RANGE.format(
                offset=offset, data_type="上市上櫃股票當日可借券賣出股數資料", count=len(data)
            )

        result = f"共有 {len(data)} 筆上市上櫃股票當日可借券賣出股數資料：\n\n"

        if page_twse:
            result += f"【上市股票】（共 {total_twse} 筆，顯示第 {offset + 1}–{min(offset + limit, total_twse)} 筆）\n"
            for item in page_twse:
                stock_code = item.get("TWSECode", "N/A")
                available_volume = item.get("TWSEAvailableVolume", "N/A")
                result += f"- 股票代號 {stock_code}: 可借券賣出股數 {available_volume}\n"
            remaining_twse = total_twse - offset - limit
            if remaining_twse > 0:
                result += f"... 還有 {remaining_twse} 筆，使用 offset={offset + limit} 查看更多\n"

        if page_gretai:
            result += f"\n【上櫃股票】（共 {total_gretai} 筆，顯示第 {offset + 1}–{min(offset + limit, total_gretai)} 筆）\n"
            for item in page_gretai:
                stock_code = item.get("GRETAICode", "N/A")
                available_volume = item.get("GRETAIAvailableVolume", "N/A")
                result += f"- 股票代號 {stock_code}: 可借券賣出股數 {available_volume}\n"
            remaining_gretai = total_gretai - offset - limit
            if remaining_gretai > 0:
                result += f"... 還有 {remaining_gretai} 筆，使用 offset={offset + limit} 查看更多\n"

        return result
