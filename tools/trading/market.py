"""Market trading tools for TWSE data."""

from utils import TWSEAPIClient

def register_tools(mcp):
    """Register market trading tools with the MCP instance."""
    
    @mcp.tool
    def get_stocks_no_price_change_first_five_days() -> str:
        """Get stocks with no price change in the first five trading days."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/TWT88U")
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
            data = TWSEAPIClient.get_data("/Announcement/BFZFZU_T")
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
            data = TWSEAPIClient.get_data("/exchangeReport/TWTB4U")
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
            data = TWSEAPIClient.get_data("/exchangeReport/TWTBAU1")
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
            data = TWSEAPIClient.get_data("/exchangeReport/TWTBAU2")
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
            data = TWSEAPIClient.get_data("/exchangeReport/MI_INDEX4")
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
        """Get top 20 stocks by trading volume in the centralized market."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/MI_INDEX20")
            if not data:
                return "目前沒有集中市場每日成交量前二十名證券資料。"
            
            result = "集中市場每日成交量前二十名證券：\n\n"
            for i, item in enumerate(data[:20], 1):
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                volume = item.get("成交量", "N/A")
                result += f"{i}. {stock_name} ({stock_code}): 成交量 {volume}\n"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_odd_lot_trading_quotes() -> str:
        """Get odd-lot trading quotes in the centralized market."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/TWT53U")
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
            data = TWSEAPIClient.get_data("/exchangeReport/TWTAWU")
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
    def get_after_hours_trading() -> str:
        """Get after-hours fixed-price trading in the centralized market."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/BFT41U")
            if not data:
                return "目前沒有集中市場盤後定價交易資料。"
            
            result = f"共有 {len(data)} 筆集中市場盤後定價交易資料：\n\n"
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
    def get_margin_loan_restrictions_announcement() -> str:
        """Get announcement of margin loan and short sale restrictions."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/BFI84U")
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
            data = TWSEAPIClient.get_data("/block/BFIAUU_d")
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
            data = TWSEAPIClient.get_data("/block/BFIAUU_m")
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
            data = TWSEAPIClient.get_data("/block/BFIAUU_y")
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
            data = TWSEAPIClient.get_data("/exchangeReport/STOCK_FIRST")
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
            data = TWSEAPIClient.get_data("/exchangeReport/TWT85U")
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
            data = TWSEAPIClient.get_data("/exchangeReport/BWIBBU_d")
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
            data = TWSEAPIClient.get_data("/exchangeReport/TWT84U")
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
        """Get market statistics of rising and falling securities."""
        try:
            data = TWSEAPIClient.get_data("/opendata/twtazu_od")
            if not data:
                return "目前沒有集中市場漲跌證券數統計表資料。"
            
            result = f"共有 {len(data)} 筆集中市場漲跌證券數統計表資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                date = item.get("日期", "N/A")
                rising_count = item.get("上漲家數", "N/A")
                falling_count = item.get("下跌家數", "N/A")
                unchanged_count = item.get("平盤家數", "N/A")
                result += f"- {date}: 上漲 {rising_count} 家, 下跌 {falling_count} 家, 平盤 {unchanged_count} 家\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_abnormal_accumulated_notice_stocks() -> str:
        """Get stocks with abnormal accumulated notice counts."""
        try:
            data = TWSEAPIClient.get_data("/announcement/notetrans")
            if not data:
                return "目前沒有集中市場公布注意累計次數異常資訊資料。"
            
            result = f"共有 {len(data)} 筆集中市場公布注意累計次數異常資訊資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                notice_count = item.get("注意累計次數", "N/A")
                result += f"- {stock_name} ({stock_code}): 注意累計次數 {notice_count}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_today_notice_stocks() -> str:
        """Get stocks announced as notice stocks today."""
        try:
            data = TWSEAPIClient.get_data("/announcement/notice")
            if not data:
                return "目前沒有集中市場當日公布注意股票資料。"
            
            result = f"共有 {len(data)} 筆集中市場當日公布注意股票資料：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                stock_code = item.get("證券代號", "N/A")
                stock_name = item.get("證券名稱", "N/A")
                notice_reason = item.get("注意原因", "N/A")
                result += f"- {stock_name} ({stock_code}): {notice_reason}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_daily_market_trading_info() -> str:
        """Get daily market trading information in the centralized market."""
        try:
            data = TWSEAPIClient.get_data("/exchangeReport/FMTQIK")
            if not data:
                return "目前沒有集中市場每日市場成交資訊。"
            
            result = f"共有 {len(data)} 筆集中市場每日市場成交資訊：\n\n"
            for item in data[:20]:  # Limit to first 20 for readability
                date = item.get("日期", "N/A")
                total_volume = item.get("總成交量", "N/A")
                total_value = item.get("總成交金額", "N/A")
                result += f"- {date}: 總成交量 {total_volume}, 總成交金額 {total_value}\n"
            
            if len(data) > 20:
                result += f"\n... 還有 {len(data) - 20} 筆資料"
            
            return result
        except Exception as e:
            return f"查詢失敗: {str(e)}"

    @mcp.tool
    def get_daily_securities_lending_volume() -> str:
        """Get daily available volume for securities lending (margin trading)."""
        try:
            data = TWSEAPIClient.get_data("/SBL/TWT96U")
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