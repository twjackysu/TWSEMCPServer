"""TWSE rwd history endpoints: 除權除息計算結果 (TWT49U), 當日沖銷交易 (TWTB4U) and
the full 價格／報酬指數 board incl. 類股指數 (MI_INDEX type=IND).

The OpenAPI versions of these (get_dividend_rights_schedule's TWT48U forecast,
get_daily_day_trading_targets, get_market_index_info) only cover the latest day.
"""

import re
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, format_list_response, DEFAULT_DISPLAY_LIMIT

TWT49U_URL = "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
TWTB4U_URL = "https://www.twse.com.tw/rwd/zh/dayTrading/TWTB4U"
MI_INDEX_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"

_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(value: str) -> str:
    """MI_INDEX's 漲跌 column is HTML (``<p style='color:red'>+</p>``); keep the text."""
    return _TAG_RE.sub("", str(value)).strip()


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE ex-rights / day-trading / index history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_exright_results_history(start_date: str, end_date: str, stock_no: str = "",
                                    limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市股票「已除權息」的計算結果歷史：除權息前收盤價、參考價、權值+息值。
        與 get_dividend_rights_schedule（未來除權息預告）不同，這是實際除權息當日的結果，
        可用來還原權息股價、計算填權息。資料自民國 92 年起。

        Args:
            start_date: 起始日期，格式 YYYYMMDD，例如 "20260101"
            end_date: 結束日期，格式 YYYYMMDD，例如 "20260831"
            stock_no: 股票代號（選填），指定則只回傳該股票
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            每筆除權息的日期、代號、名稱、除權息前收盤價、除權息參考價、權值+息值、權/息、
            漲跌停價、開盤競價基準、減除股利參考價、最近一季每股淨值與每股盈餘
        """
        resp = _client.fetch_json(
            TWT49U_URL, params={"startDate": start_date, "endDate": end_date, "response": "json"}
        )
        if not resp or resp.get("stat") != "OK":
            return f"查無 {start_date}～{end_date} 的除權除息計算結果（{(resp or {}).get('stat', '無回應')}）"
        rows = resp.get("data") or []
        if stock_no:
            rows = [r for r in rows if r[1].strip() == stock_no.strip()]

        def fmt(r):
            # r: 資料日期,股票代號,股票名稱,除權息前收盤價,除權息參考價,權值+息值,權/息,
            #    漲停價格,跌停價格,開盤競價基準,減除股利參考價,詳細資料,
            #    最近一次申報資料季別/日期,最近一次申報每股淨值,最近一次申報每股盈餘
            return (
                f"{r[0]} | {r[1]} {r[2]} | {r[6]} | 前收:{r[3]} 參考價:{r[4]} 權值+息值:{r[5]} | "
                f"漲停:{r[7]} 跌停:{r[8]} 競價基準:{r[9]} 減除股利參考價:{r[10]} | "
                f"每股淨值:{r[13]} 每股盈餘:{r[14]}\n"
            )

        return format_list_response(rows, f" {start_date}～{end_date} 除權除息計算結果", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_day_trading_history(date: str, stock_no: str = "", name: str = "",
                                limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市股票「指定日期」的當日沖銷交易統計（可回溯任意過去交易日）。
        與 get_daily_day_trading_targets（OpenAPI，僅最新一日標的清單）不同，此工具含全市場
        當沖占比與每檔個股的當沖成交股數、買賣金額。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260803"（需為交易日）
            stock_no: 股票代號（選填）
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）

        Returns:
            全市場當沖成交股數與占比、買進/賣出金額與占比；各股票的暫停先賣後買註記、
            當沖成交股數、當沖買進/賣出成交金額
        """
        resp = _client.fetch_json(
            TWTB4U_URL, params={"date": date, "selectType": "All", "response": "json"}
        )
        tables = (resp or {}).get("tables") or []
        if not resp or resp.get("stat") != "OK" or len(tables) < 2:
            return f"查無 {date} 的當日沖銷交易資料，請確認該日期為交易日（非假日或週末）"

        summary_rows = tables[0].get("data") or []
        rows = tables[1].get("data") or []
        if not summary_rows and not rows:
            return f"查無 {date} 的當日沖銷交易資料，請確認該日期為交易日（非假日或週末）"

        header = ""
        if summary_rows:
            # s: 總成交股數,占市場比重%,總買進金額,占比%,總賣出金額,占比%
            s = summary_rows[0]
            header = (
                f"全市場當沖: 成交股數 {s[0]}（占 {s[1]}%）| 買進金額 {s[2]}（占 {s[3]}%）| "
                f"賣出金額 {s[4]}（占 {s[5]}%）\n\n"
            )

        if stock_no:
            rows = [r for r in rows if r[0].strip() == stock_no.strip()]
        if name:
            rows = [r for r in rows if name in r[1]]

        def fmt(r):
            # r: 證券代號,證券名稱,暫停現股賣出後現款買進當沖註記,當沖成交股數,當沖買進金額,當沖賣出金額
            flag = "（暫停先賣後買）" if r[2].strip() == "Y" else ""
            return f"{r[0]} {r[1]}{flag} | 當沖股數:{r[3]} | 買進:{r[4]} | 賣出:{r[5]}\n"

        return header + format_list_response(rows, f" {date} 上市個股當日沖銷交易", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_twse_indices_by_date(date: str, keyword: str = "") -> str:
        """查詢「指定日期」證交所全部指數收盤：加權指數、類股指數（半導體類、金融保險類…）、
        主題指數（臺灣50、高股息…）與對應報酬指數。可回溯任意過去交易日，適合比較類股強弱。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260803"（需為交易日）
            keyword: 指數名稱關鍵字（選填），例如 "半導體"、"金融"、"報酬"

        Returns:
            每個指數的收盤指數、漲跌、漲跌點數、漲跌百分比，依「價格指數／報酬指數 ×
            證交所／跨市場／臺灣指數公司」分組
        """
        resp = _client.fetch_json(MI_INDEX_URL, params={"date": date, "type": "IND", "response": "json"})
        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的指數資料，請確認該日期為交易日（非假日或週末）"

        lines = [f"【{date} 證交所指數收盤行情】"]
        count = 0
        for table in resp.get("tables") or []:
            title = table.get("title")
            rows = table.get("data") or []
            if not title or not rows:
                continue
            if keyword:
                rows = [r for r in rows if keyword in r[0]]
                if not rows:
                    continue
            lines.append(f"\n〔{title}〕")
            for r in rows:
                # r: 指數,收盤指數,漲跌(+/-)(HTML),漲跌點數,漲跌百分比(%),特殊處理註記
                # 漲跌點數不帶正負號（正負號在 HTML 的漲跌欄），漲跌百分比本身已帶號
                lines.append(f"{r[0]}: {r[1]} | {strip_tags(r[2])}{r[3]} ({r[4]}%)")
                count += 1
        if not count:
            return f"查無 {date} 名稱包含「{keyword}」的指數" if keyword else f"查無 {date} 的指數資料"
        return "\n".join(lines)
