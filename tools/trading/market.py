"""Market trading tools for TWSE data."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register market trading tools with the MCP instance."""
    
    # Use injected client or fallback to singleton
    _client = client or TWSEAPIClient.get_instance()
    
    @mcp.tool
    def get_stocks_no_price_change_first_five_days() -> str:
        """Get stocks with no price change in the first five trading days."""
        try:
            data = _client.fetch_data("/exchangeReport/TWT88U")
            if not data:
                return "目前沒有上市個股首五日無漲跌幅資料。"
            
            result = f"共有 {len(data)} 筆上市個股首五日無漲跌幅資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                reference_price = item.get("參考價", "N/A")
                result += f"- {stock_name} ({stock_code}): 參考價 {reference_price}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_financial_program_abnormal_recommendations() -> str:
        """Get stocks abnormally recommended in financial programs."""
        try:
            data = _client.fetch_data("/Announcement/BFZFZU_T")
            if not data:
                return "目前沒有投資理財節目異常推介個股資料。"
            
            result = f"共有 {len(data)} 筆投資理財節目異常推介個股資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                program_name = item.get("節目名稱", "N/A")
                result += f"- {stock_name} ({stock_code}): {program_name}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_daily_day_trading_targets() -> str:
        """Get daily day trading targets and statistics."""
        try:
            data = _client.fetch_data("/exchangeReport/TWTB4U")
            if not data:
                return "目前沒有上市股票每日當日沖銷交易標的及統計資料。"
            
            result = f"共有 {len(data)} 筆上市股票每日當日沖銷交易標的及統計資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                day_trading_volume = item.get("當日沖銷交易量", "N/A")
                result += f"- {stock_name} ({stock_code}): 當日沖銷交易量 {day_trading_volume}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_suspended_day_trading_announcement() -> str:
        """Get announcement of suspended buy-sell-same-day trading targets."""
        try:
            data = _client.fetch_data("/exchangeReport/TWTBAU1")
            if not data:
                return "目前沒有集中市場暫停先賣後買當日沖銷交易標的預告表資料。"
            
            result = f"共有 {len(data)} 筆集中市場暫停先賣後買當日沖銷交易標的預告表資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                suspension_date = item.get("暫停日期", "N/A")
                result += f"- {stock_name} ({stock_code}): 暫停日期 {suspension_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_suspended_day_trading_history() -> str:
        """Get historical query of suspended buy-sell-same-day trading."""
        try:
            data = _client.fetch_data("/exchangeReport/TWTBAU2")
            if not data:
                return "目前沒有集中市場暫停先賣後買當日沖銷交易歷史查詢資料。"
            
            result = f"共有 {len(data)} 筆集中市場暫停先賣後買當日沖銷交易歷史查詢資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                suspension_date = item.get("暫停日期", "N/A")
                result += f"- {stock_name} ({stock_code}): 暫停日期 {suspension_date}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_cross_market_trading_info() -> str:
        """Get daily cross-market trading information for listed and OTC stocks."""
        try:
            data = _client.fetch_data("/exchangeReport/MI_INDEX4")
            if not data:
                return "目前沒有每日上市上櫃跨市場成交資訊。"
            
            result = f"共有 {len(data)} 筆每日上市上櫃跨市場成交資訊：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                date = item.get("日期", "N/A")
                market = item.get("市場別", "N/A")
                volume = item.get("成交量", "N/A")
                result += f"- {date} {market}: 成交量 {volume}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_top_20_volume_stocks() -> str:
        """Get top 20 stocks by trading volume in the centralized market.
        
        Returns information including:
        - Date: Trading date
        - Rank: Volume ranking
        - Code: Stock code
        - Name: Stock name
        - TradeVolume: Trading volume
        - Transaction: Transaction count
        - OpeningPrice: Opening price
        - HighestPrice: Highest price
        - LowestPrice: Lowest price
        - ClosingPrice: Closing price
        - Dir: Direction (+/-)
        - Change: Price change
        """
        try:
            data = _client.fetch_data("/exchangeReport/MI_INDEX20")
            if not data:
                return "目前沒有集中市場每日成交量前二十名證券資料。"
            
            # Get the date from first item
            date = data[0].get("Date", "N/A") if data else "N/A"
            
            result = f"集中市場每日成交量前二十名證券 (日期: {date}):\n\n"
            
            for item in data[:20]:
                rank = item.get("Rank", "N/A")
                code = item.get("Code", "N/A")
                name = item.get("Name", "N/A")
                volume = item.get("TradeVolume", "N/A")
                transaction = item.get("Transaction", "N/A")
                closing_price = item.get("ClosingPrice", "N/A")
                direction = item.get("Dir", "")
                change = item.get("Change", "N/A")
                
                # Format price change with direction
                change_str = f"{direction}{change}" if direction and change != "N/A" else change
                
                result += f"{rank}. {name} ({code})\n"
                result += f"   成交量: {volume} | 成交筆數: {transaction}\n"
                result += f"   收盤價: {closing_price} | 漲跌: {change_str}\n\n"
            
            return result.strip()
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_odd_lot_trading_quotes() -> str:
        """Get odd-lot trading quotes in the centralized market."""
        try:
            data = _client.fetch_data("/exchangeReport/TWT53U")
            if not data:
                return "目前沒有集中市場零股交易行情單資料。"
            
            result = f"共有 {len(data)} 筆集中市場零股交易行情單資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                price = item.get("成交價", "N/A")
                volume = item.get("成交量", "N/A")
                result += f"- {stock_name} ({stock_code}): 成交價 {price}, 成交量 {volume}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_suspended_trading_stocks() -> str:
        """Get stocks suspended from trading in the centralized market."""
        try:
            data = _client.fetch_data("/exchangeReport/TWTAWU")
            if not data:
                return "目前沒有集中市場暫停交易證券資料。"
            
            result = f"共有 {len(data)} 筆集中市場暫停交易證券資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                suspension_reason = item.get("暫停原因", "N/A")
                result += f"- {stock_name} ({stock_code}): {suspension_reason}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_after_hours_trading(code: str = "", limit: int = 20, page_number: int = 0) -> str:
        """Get after-hours fixed-price trading in the centralized market.
        
        Args:
            code: Stock code (e.g., "2330"). If empty, returns all stocks (default: "")
            limit: Maximum number of records to return (default: 20)
            page_number: Page number for pagination, 0-based (default: 0)
        """
        try:
            data = _client.fetch_data("/exchangeReport/BFT41U")
            if not data:
                return "目前沒有集中市場盤後定價交易資料。"
            
            # Filter by stock code if provided
            if code:
                filtered_data = [item for item in data if item.get("Code") == code]
                if not filtered_data:
                    return f"查無股票代碼 {code} 的盤後定價交易資料。"
                
                # For specific stock, show detailed info
                item = filtered_data[0]
                stock_name = item.get("Name", "N/A")
                trade_price = item.get("TradePrice", "N/A")
                trade_volume = item.get("TradeVolume", "N/A")
                trade_value = item.get("TradeValue", "N/A")
                transaction = item.get("Transaction", "N/A")
                bid_volume = item.get("BidVolume", "N/A")
                ask_volume = item.get("AskVolume", "N/A")
                
                result = f"{stock_name} ({code}) 盤後定價交易資訊：\n\n"
                result += f"成交價: {trade_price}\n"
                
                if trade_volume and trade_volume != "":
                    result += f"成交量: {trade_volume}\n"
                    result += f"成交金額: {trade_value}\n"
                    result += f"成交筆數: {transaction}\n"
                else:
                    result += "狀態: 無成交\n"
                
                if bid_volume and bid_volume != "":
                    result += f"委買量: {bid_volume}\n"
                if ask_volume and ask_volume != "":
                    result += f"委賣量: {ask_volume}\n"
                
                return result
            
            # Filter out items without trade data (for list view)
            traded_data = [
                item for item in data
                if item.get("TradeVolume") and item.get("TradeVolume") != ""
            ]
            
            if not traded_data:
                return "目前沒有盤後定價交易成交資料。"
            
            # Calculate pagination
            start_idx = page_number * limit
            end_idx = start_idx + limit
            total_count = len(traded_data)
            
            if start_idx >= total_count:
                return f"頁碼超出範圍。共有 {total_count} 筆資料，每頁 {limit} 筆，最大頁碼為 {(total_count - 1) // limit}。"
            
            page_data = traded_data[start_idx:end_idx]
            
            # Build result
            result = f"集中市場盤後定價交易資料（第 {page_number + 1} 頁，共 {total_count} 筆）：\n\n"
            
            for item in page_data:
                stock_code = item.get("Code", "N/A")
                stock_name = item.get("Name", "N/A")
                trade_price = item.get("TradePrice", "N/A")
                trade_volume = item.get("TradeVolume", "N/A")
                trade_value = item.get("TradeValue", "N/A")
                result += f"- {stock_name} ({stock_code})\n"
                result += f"  成交價: {trade_price} | 成交量: {trade_volume} | 成交金額: {trade_value}\n"
            
            # Show pagination info
            remaining = total_count - end_idx
            if remaining > 0:
                next_page = page_number + 1
                result += f"\n還有 {remaining} 筆資料。使用 page_number={next_page} 查看下一頁。"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_margin_loan_restrictions_announcement() -> str:
        """Get announcement of margin loan and short sale restrictions."""
        try:
            data = _client.fetch_data("/exchangeReport/BFI84U")
            if not data:
                return "目前沒有集中市場停資停券預告表資料。"
            
            result = f"共有 {len(data)} 筆集中市場停資停券預告表資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                restriction_type = item.get("限制類別", "N/A")
                result += f"- {stock_name} ({stock_code}): {restriction_type}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_block_trades_daily() -> str:
        """Get daily block trade volume and value statistics."""
        try:
            data = _client.fetch_data("/block/BFIAUU_d")
            if not data:
                return "目前沒有集中市場鉅額交易日成交量值統計資料。"
            
            result = f"共有 {len(data)} 筆集中市場鉅額交易日成交量值統計資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                date = item.get("日期", "N/A")
                trade_count = item.get("交易筆數", "N/A")
                total_value = item.get("總成交金額", "N/A")
                result += f"- {date}: {trade_count} 筆, 總成交金額 {total_value}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_block_trades_monthly() -> str:
        """Get monthly block trade volume and value statistics."""
        try:
            data = _client.fetch_data("/block/BFIAUU_m")
            if not data:
                return "目前沒有集中市場鉅額交易月成交量值統計資料。"
            
            result = f"共有 {len(data)} 筆集中市場鉅額交易月成交量值統計資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                month = item.get("月份", "N/A")
                trade_count = item.get("交易筆數", "N/A")
                total_value = item.get("總成交金額", "N/A")
                result += f"- {month}: {trade_count} 筆, 總成交金額 {total_value}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_block_trades_yearly() -> str:
        """Get yearly block trade volume and value statistics."""
        try:
            data = _client.fetch_data("/block/BFIAUU_y")
            if not data:
                return "目前沒有集中市場鉅額交易年成交量值統計資料。"
            
            result = f"共有 {len(data)} 筆集中市場鉅額交易年成交量值統計資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                year = item.get("年度", "N/A")
                trade_count = item.get("交易筆數", "N/A")
                total_value = item.get("總成交金額", "N/A")
                result += f"- {year}: {trade_count} 筆, 總成交金額 {total_value}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_first_listed_foreign_stocks_daily() -> str:
        """Get daily trading volume and value of first-listed foreign stocks."""
        try:
            data = _client.fetch_data("/exchangeReport/STOCK_FIRST")
            if not data:
                return "目前沒有每日第一上市外國股票成交量值資料。"
            
            result = f"共有 {len(data)} 筆每日第一上市外國股票成交量值資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                volume = item.get("成交量", "N/A")
                value = item.get("成交金額", "N/A")
                result += f"- {stock_name} ({stock_code}): 成交量 {volume}, 成交金額 {value}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_securities_trading_changes() -> str:
        """Get securities trading method changes in the centralized market."""
        try:
            data = _client.fetch_data("/exchangeReport/TWT85U")
            if not data:
                return "目前沒有集中市場證券變更交易資料。"
            
            result = f"共有 {len(data)} 筆集中市場證券變更交易資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                change_type = item.get("變更類別", "N/A")
                result += f"- {stock_name} ({stock_code}): {change_type}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_valuation_ratios_by_date() -> str:
        """Get stock P/E ratio, dividend yield and P/B ratio by date query."""
        try:
            data = _client.fetch_data("/exchangeReport/BWIBBU_d")
            if not data:
                return "目前沒有上市個股日本益比、殖利率及股價淨值比（依日期查詢）資料。"
            
            result = f"共有 {len(data)} 筆上市個股日本益比、殖利率及股價淨值比（依日期查詢）資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                date = item.get("日期", "N/A")
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                pe_ratio = item.get("本益比", "N/A")
                result += f"- {date} {stock_name} ({stock_code}): 本益比 {pe_ratio}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_stock_price_changes() -> str:
        """Get stock price increase/decrease range."""
        try:
            data = _client.fetch_data("/exchangeReport/TWT84U")
            if not data:
                return "目前沒有上市個股股價升降幅度資料。"
            
            result = f"共有 {len(data)} 筆上市個股股價升降幅度資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                price_change = item.get("漲跌幅", "N/A")
                result += f"- {stock_name} ({stock_code}): 漲跌幅 {price_change}%\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_market_gain_loss_statistics() -> str:
        """Get market statistics of rising and falling securities.
        
        Returns statistics including:
        - 出表日期: Report date (ROC calendar format)
        - 類型: Type (整體市場/股票/etc.)
        - 上漲: Number of rising securities
        - 漲停: Number of securities at upper limit
        - 下跌: Number of falling securities
        - 跌停: Number of securities at lower limit
        - 持平: Number of unchanged securities
        - 未成交: Number of non-traded securities
        - 無比價: Number of securities without comparison
        """
        try:
            data = _client.fetch_data("/opendata/twtazu_od")
            if not data:
                return "目前沒有集中市場漲跌證券數統計表資料。"
            
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
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_abnormal_accumulated_notice_stocks() -> str:
        """Get stocks with abnormal accumulated notice counts.
        
        Returns information including:
        - Number: Record number (0 means no data)
        - Code: Stock code
        - Name: Stock name
        - RecentlyMetAttentionSecuritiesCriteria: Recently met attention securities criteria
        """
        try:
            data = _client.fetch_data("/announcement/notetrans")
            if not data:
                return "目前沒有集中市場公布注意累計次數異常資訊資料。"
            
            # Filter out empty records (Number="0" with empty Code)
            valid_data = [item for item in data if item.get("Code", "") != ""]
            
            if not valid_data:
                return "目前沒有集中市場公布注意累計次數異常資訊資料。"
            
            result = f"共有 {len(valid_data)} 筆集中市場公布注意累計次數異常資訊資料：\n\n"
            
            for item in valid_data[:20]:  # Limit to first 20 for readability
                number = item.get("Number", "N/A")
                code = item.get("Code", "N/A")
                name = item.get("Name", "N/A")
                criteria = item.get("RecentlyMetAttentionSecuritiesCriteria", "N/A")
                
                result += f"{number}. {name} ({code})\n"
                result += f"   符合注意標準: {criteria}\n\n"
            
            if len(valid_data) > 20:
                result += f"... 還有 {len(valid_data) - 20} 筆資料\n"
            
            return result.strip()
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_today_notice_stocks() -> str:
        """Get stocks announced as notice stocks today.
        
        Returns information including:
        - Number: Record number (0 means no data)
        - Code: Stock code
        - Name: Stock name
        - NumberOfAnnouncement: Number of announcements
        - TradingInfoForAttention: Trading information for attention
        - Date: Announcement date
        - ClosingPrice: Closing price
        - PE: P/E ratio
        """
        try:
            data = _client.fetch_data("/announcement/notice")
            if not data:
                return "目前沒有集中市場當日公布注意股票資料。"
            
            # Filter out empty records (Number="0" with empty Code)
            valid_data = [item for item in data if item.get("Code", "") != ""]
            
            if not valid_data:
                return "目前沒有集中市場當日公布注意股票資料。"
            
            result = f"共有 {len(valid_data)} 筆集中市場當日公布注意股票資料：\n\n"
            
            for item in valid_data[:20]:  # Limit to first 20 for readability
                number = item.get("Number", "N/A")
                code = item.get("Code", "N/A")
                name = item.get("Name", "N/A")
                announcement_count = item.get("NumberOfAnnouncement", "N/A")
                trading_info = item.get("TradingInfoForAttention", "N/A")
                date = item.get("Date", "N/A")
                closing_price = item.get("ClosingPrice", "N/A")
                pe_ratio = item.get("PE", "N/A")
                
                result += f"{number}. {name} ({code})\n"
                result += f"   公布次數: {announcement_count} | 日期: {date}\n"
                result += f"   收盤價: {closing_price} | 本益比: {pe_ratio}\n"
                result += f"   注意事項: {trading_info}\n\n"
            
            if len(valid_data) > 20:
                result += f"... 還有 {len(valid_data) - 20} 筆資料\n"
            
            return result.strip()
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_daily_market_trading_info() -> str:
        """Get daily market trading information in the centralized market."""
        try:
            data = _client.fetch_data("/exchangeReport/FMTQIK")
            if not data:
                return "目前沒有集中市場每日市場成交資訊。"
            
            result = f"共有 {len(data)} 筆集中市場每日市場成交資訊：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                date = item.get("Date", "N/A")
                trade_volume = item.get("TradeVolume", "N/A")
                trade_value = item.get("TradeValue", "N/A")
                transaction = item.get("Transaction", "N/A")
                taiex = item.get("TAIEX", "N/A")
                change = item.get("Change", "N/A")
                result += f"- {date}: 成交量 {trade_volume}, 成交金額 {trade_value}, 成交筆數 {transaction}, 加權指數 {taiex}, 漲跌 {change}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_daily_securities_lending_volume() -> str:
        """Get daily available volume for securities lending (margin trading)."""
        try:
            data = _client.fetch_data("/SBL/TWT96U")
            if not data:
                return "目前沒有上市上櫃股票當日可借券賣出股數資料。"
            
            result = f"共有 {len(data)} 筆上市上櫃股票當日可借券賣出股數資料：\n\n"
            
            # Separate TWSE and GRETAI data
            twse_data = [item for item in data if item.get("TWSECode")]
            gretai_data = [item for item in data if item.get("GRETAICode")]
            
            if twse_data:
                result += "【上市股票】\n"
                for item in twse_data[:15]:  # Limit to first 15 for readability
                    stock_code = item.get("TWSECode", "N/A")
                    available_volume = item.get("TWSEAvailableVolume", "N/A")
                    result += f"- 股票代號 {stock_code}: 可借券賣出股數 {available_volume}\n"
                
                if len(twse_data) > 15:
                    result += f"... 還有 {len(twse_data) - 15} 筆上市股票資料\n"
            
            if gretai_data:
                result += "\n【上櫃股票】\n"
                for item in gretai_data[:15]:  # Limit to first 15 for readability
                    stock_code = item.get("GRETAICode", "N/A")
                    available_volume = item.get("GRETAIAvailableVolume", "N/A")
                    result += f"- 股票代號 {stock_code}: 可借券賣出股數 {available_volume}\n"
                
                if len(gretai_data) > 15:
                    result += f"... 還有 {len(gretai_data) - 15} 筆上櫃股票資料\n"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"