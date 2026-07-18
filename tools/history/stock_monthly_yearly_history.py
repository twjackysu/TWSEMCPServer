"""TWSE per-stock monthly/yearly aggregated trading history."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

FMSRFK_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMSRFK"
FMNPTK_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMNPTK"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE per-stock monthly/yearly history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_monthly_history(stock_no: str, date: str) -> str:
        """查詢個股月成交資訊（最高價、最低價、加權平均價、週轉率）。
        與 get_stock_monthly_avg_history（每日的月均價序列）不同，此工具是「每月一筆」的彙總。
        只有 date 的年份會影響查詢結果：查當年會回傳至今每月資料，查過去年份則回傳該年全部12個月。

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）
            date: 任意日期 YYYYMMDD，僅年份有效，例如 "20250101" 查民國114年整年

        Returns:
            該年度每月的最高價、最低價、加權平均價、成交筆數、成交金額、成交股數、週轉率
        """
        resp = _client.fetch_json(
            FMSRFK_URL,
            params={"response": "json", "date": date, "stockNo": stock_no},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無股票代號 {stock_no} 的月成交資訊，請確認代號是否正確"

        data = resp.get("data", [])
        if not data:
            return f"查無股票代號 {stock_no} 的月成交資訊"

        title = resp.get("title", f"{stock_no} 月成交資訊")
        lines = [f"【{title}】\n"]
        for row in data:
            # row: 年度,月份,最高價,最低價,加權(A/B)平均價,成交筆數,成交金額(A),成交股數(B),週轉率(%)
            year, month, high, low, avg, tx, value, volume, turnover = row
            lines.append(
                f"{year}/{int(month):02d} | 最高:{high} 最低:{low} 加權均價:{avg} | "
                f"量:{volume} 金額:{value} 筆數:{tx} | 週轉率:{turnover}%"
            )

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_stock_yearly_history(stock_no: str) -> str:
        """查詢個股歷年成交資訊（最高價、最低價、收盤平均價），資料可回溯數十年。
        與 get_stock_monthly_history（單一年度逐月）互補，此工具是「每年一筆」的長期彙總，
        適合看個股長期價格區間演變。

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）

        Returns:
            每年度的最高價（及日期）、最低價（及日期）、收盤平均價、成交股數、成交金額、成交筆數
        """
        resp = _client.fetch_json(
            FMNPTK_URL,
            params={"response": "json", "date": "20260101", "stockNo": stock_no},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無股票代號 {stock_no} 的歷年成交資訊，請確認代號是否正確"

        tables = resp.get("tables", [])
        yearly_table = tables[0] if tables else None
        data = yearly_table.get("data") if yearly_table else None
        if not data:
            return f"查無股票代號 {stock_no} 的歷年成交資訊"

        lines = [f"【{stock_no} 歷年成交資訊】（共 {len(data)} 年）\n"]
        for row in data:
            # row: 年度,成交股數,成交金額,成交筆數,最高價,日期(最高),最低價,日期(最低),收盤平均價
            year, volume, value, tx, high, high_date, low, low_date, avg_close = row
            lines.append(
                f"{year}年 | 最高:{high}（{high_date}） 最低:{low}（{low_date}） 收盤均價:{avg_close} | "
                f"量:{volume} 金額:{value} 筆數:{tx}"
            )

        return "\n".join(lines)
