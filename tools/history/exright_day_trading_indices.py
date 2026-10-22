"""TWSE rwd endpoints: 除權除息計算結果 (TWT49U), 當日沖銷交易 (TWTB4U) and the full
價格／報酬指數 board incl. 類股指數 (MI_INDEX type=IND).

Each returns the latest trading day when ``date`` is omitted and any past date otherwise.
The day-trading and index tools replace OpenAPI versions (/exchangeReport/TWTB4U,
/exchangeReport/MI_INDEX) that only covered the latest day with fewer columns.
"""

from datetime import datetime
from typing import Literal, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, format_list_response, DEFAULT_DISPLAY_LIMIT, printed
from toolkit import Limit, Offset, RequiredTradingDate, TradingDate, handle_api_errors
from sources.twse.mi_index import index_quotes
from sources.twse.twt49u import exright_results

TWTB4U_URL = "https://www.twse.com.tw/rwd/zh/dayTrading/TWTB4U"


def _any(*patterns):
    return lambda name: any(p in name for p in patterns)


def _is_return(name: str) -> bool:
    return "報酬指數" in name


# 指數名稱 → 是否屬於該分類（沿用原 OpenAPI 版 get_market_index_info 的分類規則）
IndexCategory = Literal["major", "sector", "esg", "leverage", "return", "thematic", "dividend", "all"]  # INDEX_CATEGORIES
INDEX_CATEGORIES = {
    "major": lambda n: (_any("發行量加權", "寶島", "臺灣50", "中型", "小型", "未含", "公司治理", "高股息")(n)
                        and not _any("類指數", "報酬指數", "兩倍", "反向", "槓桿")(n)),
    "sector": lambda n: "類指數" in n and not _is_return(n),
    "esg": _any("ESG", "永續", "公司治理", "社會責任", "環境", "綠能", "低碳", "友善"),
    "leverage": _any("兩倍", "反向", "槓桿"),
    "return": _is_return,
    "thematic": lambda n: _any("AI", "5G", "生技", "電動車", "綠能", "半導體", "科技", "創新")(n) and not _is_return(n),
    "dividend": lambda n: _any("高股息", "高息", "股息", "股利", "優息", "存股")(n) and not _is_return(n),
    "all": lambda n: True,
}


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE ex-rights / day-trading / index history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_exright_results_history(start_date: RequiredTradingDate, end_date: RequiredTradingDate, stock_no: str = "",
                                    limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上市股票「已除權息」的計算結果歷史：除權息前收盤價、參考價、權值+息值。
        與 get_dividend_rights_schedule（未來除權息預告）不同，這是實際除權、除息當日的結果，
        可用來還原權息股價、計算填權息（填息）。資料自民國 92 年起。

        回傳：每筆除權息的日期、代號、名稱、除權息前收盤價、除權息參考價、權值+息值、權/息、
        漲跌停價、開盤競價基準、減除股利參考價、最近一季每股淨值與每股盈餘

        Args:
            start_date: 起始日期，格式 西元 YYYYMMDD，例如 "20260101"
            end_date: 結束日期，格式 西元 YYYYMMDD，例如 "20260831"
            stock_no: 股票代號（選填），指定則只回傳該股票
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        start, end = (datetime.strptime(d, "%Y%m%d").date() for d in (start_date, end_date))

        report = exright_results(_client, start, end)
        if not report.found:
            return f"查無 {start_date}～{end_date} 的除權除息計算結果（{report.stat}）"
        rows = report.results
        if stock_no:
            rows = [r for r in rows if r.code == stock_no.strip()]

        def fmt(r):
            return (
                f"{r.day.year - 1911}年{r.day:%m}月{r.day:%d}日 | {r.code} {r.name} | {r.kind} | "
                f"前收:{printed(r.close_before)} 參考價:{printed(r.reference)} 權值+息值:{printed(r.rights_and_dividend)} | "
                f"漲停:{printed(r.limit_up)} 跌停:{printed(r.limit_down)} 競價基準:{printed(r.opening_reference)} "
                f"減除股利參考價:{printed(r.ex_dividend_reference)} | 每股淨值:{r.nav_per_share} 每股盈餘:{r.eps}\n"
            )

        return format_list_response(rows, f" {start_date}～{end_date} 除權除息計算結果", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_daily_day_trading_targets(date: TradingDate = "", stock_no: str = "", name: str = "",
                                      limit: Limit = DEFAULT_DISPLAY_LIMIT, offset: Offset = 0) -> str:
        """查詢上市股票當日沖銷交易標的與統計：預設最新交易日，也可回溯任意過去交易日。
        含全市場當沖占比、每檔可當沖股票的「暫停先賣後買」註記、當沖成交股數與買賣金額。
        證交所於交易日晚間才公布當日量值（T+2 前仍可能修正），盤中查詢當天可能只有標的清單。

        回傳：全市場當沖成交股數與占比、買進/賣出金額與占比；各股票的暫停先賣後買註記、
        當沖成交股數、當沖買進/賣出成交金額

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260803"（選填，留空＝最新交易日）
            stock_no: 股票代號（選填）
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        params = {"selectType": "All", "response": "json"}
        if date.strip():
            params["date"] = date.strip()
        resp = _client.fetch_json(TWTB4U_URL, params=params)
        tables = (resp or {}).get("tables") or []
        label = date or "最新交易日"
        if not resp or resp.get("stat") != "OK" or len(tables) < 2:
            return f"查無 {label} 的當日沖銷交易資料，請確認該日期為交易日（非假日或週末）"

        summary_rows = tables[0].get("data") or []
        rows = tables[1].get("data") or []
        if not summary_rows and not rows:
            return f"查無 {label} 的當日沖銷交易資料，請確認該日期為交易日（非假日或週末）"
        day = resp.get("date") or label

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

        # 證交所於交易日晚間才公布量值；在那之前當天的個股表只有「代號、名稱、註記」三格
        if not any(len(r) >= 6 for r in rows):
            header += "（當日當沖量值尚未公布，以下僅列可當沖標的）\n\n"

        def fmt(r):
            # r: 證券代號,證券名稱,暫停現股賣出後現款買進當沖註記,當沖成交股數,當沖買進金額,當沖賣出金額
            flag = "（暫停先賣後買）" if len(r) > 2 and r[2].strip() == "Y" else ""
            if len(r) < 6:
                return f"{r[0]} {r[1]}{flag}\n"
            return f"{r[0]} {r[1]}{flag} | 當沖股數:{r[3]} | 買進:{r[4]} | 賣出:{r[5]}\n"

        return header + format_list_response(rows, f" {day} 上市個股當日沖銷交易", fmt, limit, offset)

    @mcp.tool
    @handle_api_errors()
    def get_market_index_info(date: TradingDate = "", category: IndexCategory = "major", keyword: str = "") -> str:
        """查詢證交所指數收盤行情：預設最新交易日，也可回溯任意過去交易日，適合比較類股強弱。
        涵蓋加權指數、類股指數（半導體類、金融保險類…）、主題指數（臺灣50、高股息…）與報酬指數。

        回傳：每個指數的收盤指數、漲跌點數、漲跌百分比，依「價格指數／報酬指數 ×
        證交所／跨市場／臺灣指數公司」分組

        Args:
            date: 查詢日期，格式 西元 YYYYMMDD，例如 "20260803"（選填，留空＝最新交易日）
            category: 指數分類：
                - "major": 主要市場指數（加權、寶島、臺灣50、中型100等，預設）
                - "sector": 產業類指數（半導體類、金融保險類等）
                - "esg": ESG永續、公司治理相關指數
                - "leverage": 槓桿及反向指數
                - "return": 報酬指數（含股息再投資）
                - "thematic": 主題指數（AI、5G、半導體、電動車等）
                - "dividend": 高股息相關指數
                - "all": 所有指數
            keyword: 指數名稱關鍵字（選填），例如 "半導體"；與 category 同時套用
        """
        matcher = INDEX_CATEGORIES[category]
        board = index_quotes(_client, date.strip())
        label = date or "最新交易日"
        if board is None:
            return f"查無 {label} 的指數資料，請確認該日期為交易日（非假日或週末）"

        lines = [f"【{board.date or label} 證交所指數收盤行情（{category}）】"]
        count = 0
        for table in board.tables:
            quotes = [q for q in table.quotes if matcher(q.name) and keyword in q.name]
            if not quotes:
                continue
            lines.append(f"\n〔{table.title}〕")
            for q in quotes:
                # 漲跌點數不帶正負號（方向另成一欄），漲跌百分比本身已帶號
                lines.append(f"{q.name}: {printed(q.close)} | {q.direction}{printed(q.change_points)} "
                             f"({printed(q.change_pct)}%)")
                count += 1
        if not count:
            cond = f"分類 {category}" + (f"、名稱包含「{keyword}」" if keyword else "")
            return f"查無 {label} 符合{cond}的指數"
        return "\n".join(lines)
