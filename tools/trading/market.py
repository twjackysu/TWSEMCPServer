"""Market trading tools for TWSE data."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    MSG_NO_DATA,
    handle_api_errors,
    format_list_response,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market trading tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(data_type="上市個股首五日無漲跌幅")
    def get_stocks_no_price_change_first_five_days(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市個股首五日無漲跌幅。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWT88U")
        if not data:
            return MSG_NO_DATA.format(data_type="上市個股首五日無漲跌幅")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            reference_price = item.get("PriceUnderwritten", "N/A")
            return f"- {stock_name} ({stock_code}): 承銷價 {reference_price}\n"

        return format_list_response(data, "上市個股首五日無漲跌幅資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="投資理財節目異常推介個股")
    def get_financial_program_abnormal_recommendations(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢投資理財節目異常推介個股。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/Announcement/BFZFZU_T")
        if not data:
            return MSG_NO_DATA.format(data_type="投資理財節目異常推介個股")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            program_name = item.get("Number", "N/A")
            return f"- {stock_name} ({stock_code}): {program_name}\n"

        return format_list_response(data, "投資理財節目異常推介個股資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="上市股票每日當日沖銷交易標的")
    def get_daily_day_trading_targets(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市股票每日當日沖銷交易標的及統計。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWTB4U")
        if not data:
            return MSG_NO_DATA.format(data_type="上市股票每日當日沖銷交易標的")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            suspension = item.get("Suspension", "N/A")
            return f"- {stock_name} ({stock_code}): {suspension}\n"

        return format_list_response(data, "上市股票每日當日沖銷交易標的資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場暫停先賣後買當日沖銷交易標的預告表")
    def get_suspended_day_trading_announcement(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場暫停先賣後買當日沖銷交易標的預告表。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWTBAU1")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場暫停先賣後買當日沖銷交易標的預告表")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            suspension_date = item.get("StartDate", "N/A")
            return f"- {stock_name} ({stock_code}): 暫停日期 {suspension_date}\n"

        return format_list_response(data, "集中市場暫停先賣後買當日沖銷交易標的預告表資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場暫停先賣後買當日沖銷交易歷史")
    def get_suspended_day_trading_history(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場暫停先賣後買當日沖銷交易歷史查詢。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWTBAU2")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場暫停先賣後買當日沖銷交易歷史")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            suspension_date = item.get("StartDate", "N/A")
            return f"- {stock_name} ({stock_code}): 暫停日期 {suspension_date}\n"

        return format_list_response(data, "集中市場暫停先賣後買當日沖銷交易歷史資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="每日上市上櫃跨市場成交資訊")
    def get_cross_market_trading_info(limit: int = 50, offset: int = 0) -> str:
        """查詢每日上市上櫃跨市場成交資訊。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/MI_INDEX4")
        if not data:
            return MSG_NO_DATA.format(data_type="每日上市上櫃跨市場成交資訊")

        def formatter(item):
            date = item.get("Date", "N/A")
            index = item.get("FormosaIndex", "N/A")
            change = item.get("Change", "N/A")
            value = item.get("TradeValue", "N/A")
            return f"- {date}: 台灣指數 {index} ({change}) 成交金額 {value}\n"

        return format_list_response(data, "每日上市上櫃跨市場成交資訊", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場每日成交量前二十名證券")
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
    @handle_api_errors(data_type="集中市場零股交易行情單")
    def get_odd_lot_trading_quotes(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場零股交易行情單。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWT53U")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場零股交易行情單")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            price = item.get("TradePrice", "N/A")
            volume = item.get("TradeVolume", "N/A")
            return f"- {stock_name} ({stock_code}): 成交價 {price}, 成交量 {volume}\n"

        return format_list_response(data, "集中市場零股交易行情單資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場暫停交易證券")
    def get_suspended_trading_stocks(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場暫停交易證券。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWTAWU")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場暫停交易證券")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            halt_date = item.get("TradingHaltDate", "N/A")
            resumption_date = item.get("TradingResumptionDate", "N/A")
            return f"- {stock_name} ({stock_code}): 停止 {halt_date}, 恢復 {resumption_date}\n"

        return format_list_response(data, "集中市場暫停交易證券資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場盤後定價交易")
    def get_after_hours_trading(code: str = "", limit: int = 50, offset: int = 0) -> str:
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
    @handle_api_errors(data_type="集中市場停資停券預告表")
    def get_margin_loan_restrictions_announcement(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場停資停券預告表。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/BFI84U")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場停資停券預告表")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            restriction_type = item.get("Reason", "N/A")
            return f"- {stock_name} ({stock_code}): {restriction_type}\n"

        return format_list_response(data, "集中市場停資停券預告表資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場鉅額交易日成交量值統計")
    def get_block_trades_daily(limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場鉅額交易日成交量值統計。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/block/BFIAUU_d")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場鉅額交易日成交量值統計")

        def formatter(item):
            date = item.get("Date", "N/A")
            volume = item.get("TradeVolume", "N/A")
            total_value = item.get("TradeValue", "N/A")
            return f"- {date}: 成交量 {volume}, 總成交金額 {total_value}\n"

        return format_list_response(data, "集中市場鉅額交易日成交量值統計資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場鉅額交易月成交量值統計")
    def get_block_trades_monthly(limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場鉅額交易月成交量值統計。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/block/BFIAUU_m")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場鉅額交易月成交量值統計")

        def formatter(item):
            month = item.get("Month", "N/A")
            volume = item.get("TradeVolume", "N/A")
            total_value = item.get("TradeValue", "N/A")
            return f"- {month}: 成交量 {volume}, 總成交金額 {total_value}\n"

        return format_list_response(data, "集中市場鉅額交易月成交量值統計資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場鉅額交易年成交量值統計")
    def get_block_trades_yearly(limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場鉅額交易年成交量值統計。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/block/BFIAUU_y")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場鉅額交易年成交量值統計")

        def formatter(item):
            year = item.get("Month", "N/A")
            volume = item.get("TradeVolume", "N/A")
            total_value = item.get("TradeValue", "N/A")
            return f"- {year}: 成交量 {volume}, 總成交金額 {total_value}\n"

        return format_list_response(data, "集中市場鉅額交易年成交量值統計資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="每日第一上市外國股票成交量值")
    def get_first_listed_foreign_stocks_daily(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢每日第一上市外國股票成交量值。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/STOCK_FIRST")
        if not data:
            return MSG_NO_DATA.format(data_type="每日第一上市外國股票成交量值")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            volume = item.get("TradeVolume", "N/A")
            value = item.get("TradeValue", "N/A")
            return f"- {stock_name} ({stock_code}): 成交量 {volume}, 成交金額 {value}\n"

        return format_list_response(data, "每日第一上市外國股票成交量值資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場證券變更交易")
    def get_securities_trading_changes(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場證券變更交易。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWT85U")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場證券變更交易")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            change_type = item.get("PeriodicCallAuctionTrading", "N/A")
            return f"- {stock_name} ({stock_code}): {change_type}\n"

        return format_list_response(data, "集中市場證券變更交易資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="上市個股日本益比殖利率及股價淨值比")
    def get_valuation_ratios_by_date(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市個股日本益比、殖利率及股價淨值比（依日期查詢）。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/BWIBBU_d")
        if not data:
            return MSG_NO_DATA.format(data_type="上市個股日本益比殖利率及股價淨值比")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            dividend_yield = item.get("DividendYield", "N/A")
            dividend_year = item.get("DividendYear", "N/A")
            pe_ratio = item.get("PEratio", "N/A")
            pb_ratio = item.get("PBratio", "N/A")
            fiscal_year_quarter = item.get("FiscalYearQuarter", "N/A")
            return (
                f"- {stock_name} ({stock_code})\n"
                f"  本益比: {pe_ratio} | 殖利率: {dividend_yield}% (股利年度: {dividend_year})\n"
                f"  股價淨值比: {pb_ratio} | 財報季度: {fiscal_year_quarter}\n\n"
            )

        return format_list_response(data, "上市個股日本益比殖利率及股價淨值比資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="上市個股股價升降幅度")
    def get_stock_price_changes(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市個股股價升降幅度。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/TWT84U")
        if not data:
            return MSG_NO_DATA.format(data_type="上市個股股價升降幅度")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            limit_up = item.get("TodayLimitUp", "N/A")
            limit_down = item.get("TodayLimitDown", "N/A")
            return f"- {stock_name} ({stock_code}): 漲停 {limit_up}, 跌停 {limit_down}\n"

        return format_list_response(data, "上市個股股價升降幅度資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="集中市場漲跌證券數統計表")
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
    @handle_api_errors(data_type="集中市場公布注意累計次數異常資訊")
    def get_abnormal_accumulated_notice_stocks(name: str = "", limit: int = 50, offset: int = 0) -> str:
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
    @handle_api_errors(data_type="集中市場當日公布注意股票")
    def get_today_notice_stocks(name: str = "", limit: int = 50, offset: int = 0) -> str:
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
    @handle_api_errors(data_type="集中市場每日市場成交資訊")
    def get_daily_market_trading_info(limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場每日市場成交資訊。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/exchangeReport/FMTQIK")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場每日市場成交資訊")

        def formatter(item):
            date = item.get("Date", "N/A")
            trade_volume = item.get("TradeVolume", "N/A")
            trade_value = item.get("TradeValue", "N/A")
            transaction = item.get("Transaction", "N/A")
            taiex = item.get("TAIEX", "N/A")
            change = item.get("Change", "N/A")
            return f"- {date}: 成交量 {trade_volume}, 成交金額 {trade_value}, 成交筆數 {transaction}, 加權指數 {taiex}, 漲跌 {change}\n"

        return format_list_response(data, "集中市場每日市場成交資訊", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="上市上櫃股票當日可借券賣出股數")
    def get_daily_securities_lending_volume(limit: int = 50, offset: int = 0) -> str:
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
        result = f"共有 {len(data)} 筆上市上櫃股票當日可借券賣出股數資料：\n\n"

        if twse_data:
            page_twse = twse_data[offset:offset + limit]
            result += f"【上市股票】（共 {total_twse} 筆，顯示第 {offset + 1}–{min(offset + limit, total_twse)} 筆）\n"
            for item in page_twse:
                stock_code = item.get("TWSECode", "N/A")
                available_volume = item.get("TWSEAvailableVolume", "N/A")
                result += f"- 股票代號 {stock_code}: 可借券賣出股數 {available_volume}\n"
            remaining_twse = total_twse - offset - limit
            if remaining_twse > 0:
                result += f"... 還有 {remaining_twse} 筆，使用 offset={offset + limit} 查看更多\n"

        if gretai_data:
            page_gretai = gretai_data[offset:offset + limit]
            result += f"\n【上櫃股票】（共 {total_gretai} 筆，顯示第 {offset + 1}–{min(offset + limit, total_gretai)} 筆）\n"
            for item in page_gretai:
                stock_code = item.get("GRETAICode", "N/A")
                available_volume = item.get("GRETAIAvailableVolume", "N/A")
                result += f"- 股票代號 {stock_code}: 可借券賣出股數 {available_volume}\n"
            remaining_gretai = total_gretai - offset - limit
            if remaining_gretai > 0:
                result += f"... 還有 {remaining_gretai} 筆，使用 offset={offset + limit} 查看更多\n"

        return result
