"""TWSE listed stocks institutional (三大法人) trading data."""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"

# Column indices in the data array (based on T86 fields)
IDX_CODE = 0          # 證券代號
IDX_NAME = 1          # 證券名稱
IDX_FK_BUY = 2        # 外陸資買進股數(不含外資自營商)
IDX_FK_SELL = 3       # 外陸資賣出股數(不含外資自營商)
IDX_FK_NET = 4        # 外陸資買賣超股數(不含外資自營商)
IDX_FKDL_BUY = 5      # 外資自營商買進股數
IDX_FKDL_SELL = 6     # 外資自營商賣出股數
IDX_FKDL_NET = 7      # 外資自營商買賣超股數
IDX_IT_BUY = 8        # 投信買進股數
IDX_IT_SELL = 9       # 投信賣出股數
IDX_IT_NET = 10       # 投信買賣超股數
IDX_DL_NET = 11       # 自營商買賣超股數
IDX_DL_BUY_SELF = 12  # 自營商買進股數(自行買賣)
IDX_DL_SELL_SELF = 13 # 自營商賣出股數(自行買賣)
IDX_DL_NET_SELF = 14  # 自營商買賣超股數(自行買賣)
IDX_DL_BUY_HEDGE = 15 # 自營商買進股數(避險)
IDX_DL_SELL_HEDGE = 16# 自營商賣出股數(避險)
IDX_DL_NET_HEDGE = 17 # 自營商買賣超股數(避險)
IDX_TOTAL_NET = 18    # 三大法人買賣超股數


def _parse_num(value: str) -> int:
    """Convert comma-separated number string to int."""
    try:
        return int(value.replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def _fmt(value: str) -> str:
    """Return value as-is (keep original formatted string)."""
    return value or "-"


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TWSE listed stocks institutional investor tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_twse_institutional_investors_summary(date: str) -> str:
        """查詢台灣上市市場三大法人（外資、投信、自營商）買賣超日報。
        回傳指定日期所有上市股票的三大法人買賣超彙總，並依買賣超絕對值排序，顯示前 30 名。

        Args:
            date: 查詢日期，格式 YYYYMMDD，例如 "20260505"（需為交易日）

        Returns:
            上市股票三大法人買賣超日報，含外資、投信、自營商各別及合計買賣超股數
        """
        resp = _client.fetch_json(
            T86_URL,
            params={"response": "json", "date": date, "selectType": "ALL"},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的三大法人買賣超資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的三大法人買賣超資料"

        title = resp.get("title", f"{date} 三大法人買賣超日報")

        # Filter rows where any institutional investor has non-zero net
        # Some rows (e.g. bond ETFs) have fewer than 19 columns — skip them
        active = [row for row in data if len(row) > IDX_TOTAL_NET and _parse_num(row[IDX_TOTAL_NET]) != 0]

        # Sort by absolute value of total net descending
        active.sort(key=lambda r: abs(_parse_num(r[IDX_TOTAL_NET])), reverse=True)

        lines = [f"【{title}】（共 {len(active)} 支有法人進出，顯示前 30 名）\n"]

        for row in active[:30]:
            code = row[IDX_CODE]
            name = row[IDX_NAME]
            fk_net = _fmt(row[IDX_FK_NET])
            it_net = _fmt(row[IDX_IT_NET])
            dl_net = _fmt(row[IDX_DL_NET])
            total = _fmt(row[IDX_TOTAL_NET])

            lines.append(
                f"{code} {name} | 外資: {fk_net} | 投信: {it_net} | "
                f"自營: {dl_net} | 合計: {total}"
            )

        if len(active) > 30:
            lines.append(f"\n...還有 {len(active) - 30} 筆資料未顯示")

        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors()
    def get_twse_institutional_investors_by_stock(stock_no: str, date: str) -> str:
        """查詢指定上市股票的三大法人（外資、投信、自營商）買賣超明細。
        回傳外資（含外資自營商）、投信、自營商（含自行買賣與避險）的完整買進、賣出、買賣超股數。

        Args:
            stock_no: 股票代號，例如 "2330"（台積電）、"0050"（元大台灣50）
            date: 查詢日期，格式 YYYYMMDD，例如 "20260505"（需為交易日）

        Returns:
            該股票三大法人完整買賣超明細，含外資、外資自營商、投信、自營商各細項
        """
        resp = _client.fetch_json(
            T86_URL,
            params={"response": "json", "date": date, "selectType": "ALL"},
        )

        if not resp or resp.get("stat") != "OK":
            return f"查無 {date} 的三大法人買賣超資料，請確認該日期為交易日（非假日或週末）"

        data = resp.get("data", [])
        if not data:
            return f"查無 {date} 的三大法人買賣超資料"

        # Filter by stock code; skip rows with insufficient columns
        row = next((r for r in data if len(r) > IDX_TOTAL_NET and r[IDX_CODE] == stock_no), None)
        if not row:
            return f"查無上市股票代號 {stock_no} 在 {date} 的三大法人資料"

        title = resp.get("title", f"{date} 三大法人買賣超日報")
        name = row[IDX_NAME]

        lines = [
            f"【{title}】",
            f"股票代號：{row[IDX_CODE]}  股票名稱：{name}\n",
            "─── 外資及陸資（不含外資自營商）───",
            f"  買進：{_fmt(row[IDX_FK_BUY])} 股",
            f"  賣出：{_fmt(row[IDX_FK_SELL])} 股",
            f"  買賣超：{_fmt(row[IDX_FK_NET])} 股",
            "",
            "─── 外資自營商 ───",
            f"  買進：{_fmt(row[IDX_FKDL_BUY])} 股",
            f"  賣出：{_fmt(row[IDX_FKDL_SELL])} 股",
            f"  買賣超：{_fmt(row[IDX_FKDL_NET])} 股",
            "",
            "─── 投信 ───",
            f"  買進：{_fmt(row[IDX_IT_BUY])} 股",
            f"  賣出：{_fmt(row[IDX_IT_SELL])} 股",
            f"  買賣超：{_fmt(row[IDX_IT_NET])} 股",
            "",
            "─── 自營商 ───",
            f"  自行買賣 買進：{_fmt(row[IDX_DL_BUY_SELF])} 股",
            f"  自行買賣 賣出：{_fmt(row[IDX_DL_SELL_SELF])} 股",
            f"  自行買賣 買賣超：{_fmt(row[IDX_DL_NET_SELF])} 股",
            f"  避險 買進：{_fmt(row[IDX_DL_BUY_HEDGE])} 股",
            f"  避險 賣出：{_fmt(row[IDX_DL_SELL_HEDGE])} 股",
            f"  避險 買賣超：{_fmt(row[IDX_DL_NET_HEDGE])} 股",
            f"  合計買賣超：{_fmt(row[IDX_DL_NET])} 股",
            "",
            "═══ 三大法人合計買賣超 ═══",
            f"  {_fmt(row[IDX_TOTAL_NET])} 股",
        ]

        return "\n".join(lines)
