"""TWSE per-stock monthly/yearly aggregated trading history.

Replaces the OpenAPI /exchangeReport/FMSRFK_ALL and FMNPTK_ALL tools: per stock they only
gave the latest month / year, whose values on 2026-09-29 equalled this endpoint's rows for
that month / year; these endpoints return the whole year / all years. Read through the
FMSRFK / FMNPTK gateways (``sources.twse.fmsrfk`` / ``sources.twse.fmnptk``).
"""

from typing import Optional
from fastmcp import FastMCP
from sources.twse.fmnptk import yearly_trading
from sources.twse.fmsrfk import monthly_trading
from utils import TWSEAPIClient, printed
from utils.date_helper import taipei_today
from toolkit import TradingDate, handle_api_errors


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE per-stock monthly/yearly history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_monthly_trading(stock_no: str, date: TradingDate = "") -> str:
        """查詢上市個股月成交資訊（每月一筆：最高價、最低價、加權平均價、成交量值、週轉率）。
        預設今年至今每個月，也可查過去年度的全部 12 個月。

        回傳：該年度每月的最高價、最低價、加權平均價、成交筆數、成交金額、成交股數、週轉率

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）
            date: 任意日期 西元 YYYYMMDD，僅年份有效，例如 "20250101" 查民國114年整年（留空＝今年）
        """
        year = monthly_trading(_client, stock_no, date)
        if year is None:
            return f"查無股票代號 {stock_no} 的月成交資訊，請確認代號是否正確"
        if not year.months:
            return f"查無股票代號 {stock_no} 的月成交資訊"

        lines = [f"【{year.title or f'{stock_no} 月成交資訊'}】\n"]
        for m in year.months:
            lines.append(
                f"{m.year}/{m.month:02d} | 最高:{printed(m.high)} 最低:{printed(m.low)} 加權均價:{printed(m.average)} | "
                f"量:{printed(m.volume)} 金額:{printed(m.value)} 筆數:{printed(m.transactions)} | "
                f"週轉率:{printed(m.turnover)}%"
            )

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_yearly_trading(stock_no: str) -> str:
        """查詢個股歷年成交資訊（最高價、最低價、收盤平均價），資料可回溯數十年。
        與 get_stock_monthly_trading（單一年度逐月）互補，此工具是「每年一筆」的長期彙總，
        適合看個股長期價格區間演變。

        回傳：每年度的最高價（及日期）、最低價（及日期）、收盤平均價、成交股數、成交金額、成交筆數

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）
        """
        # FMNPTK 以 date 的年份當作歷年序列的終點。這裡原本寫死 "20260101"，等於把終點
        # 凍結在當初寫程式的年份：跨年之後最新年度會從結果中默默消失（輸出格式完全正常，
        # 只是少一列）。此工具不收日期參數——查的就是「到今天為止的歷年」——所以每次呼叫
        # 都以當天日期查詢。
        years = yearly_trading(_client, stock_no, f"{taipei_today():%Y%m%d}")
        if years is None:
            return f"查無股票代號 {stock_no} 的歷年成交資訊，請確認代號是否正確"
        if not years:
            return f"查無股票代號 {stock_no} 的歷年成交資訊"

        lines = [f"【{stock_no} 歷年成交資訊】（共 {len(years)} 年）\n"]
        for y in years:
            lines.append(
                f"{y.year}年 | 最高:{printed(y.high)}（{y.high_date}） 最低:{printed(y.low)}（{y.low_date}） "
                f"收盤均價:{printed(y.average_close)} | "
                f"量:{printed(y.volume)} 金額:{printed(y.value)} 筆數:{printed(y.transactions)}"
            )

        return "\n".join(lines)
