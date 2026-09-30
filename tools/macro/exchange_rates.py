"""中央銀行 daily inter-bank exchange rates (我國與主要貿易對手通貨對美元之匯率).

cpx.cbc.gov.tw's DataAPI serves dataset BP01D01 as JSON: ``data.structure.Table1`` names
the currency columns and ``data.dataSets`` holds one row per day (``[YYYYMMDD, ...]``)
back to 1993. CBC refreshes the file about monthly, so the latest weeks may be missing.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

CBC_FX_URL = "https://cpx.cbc.gov.tw/API/DataAPI/Get"
CBC_FX_FILE = "BP01D01"
DEFAULT_DAYS = 10
MAX_DAYS = 120
# The whole 1993-to-date file (~1.3 MB) comes back on every request and CBC refreshes it
# about monthly.
CBC_CACHE_TTL = 3600


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register CBC exchange-rate tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_exchange_rates(start_date: str = "", end_date: str = "", currency: str = "") -> str:
        """查詢中央銀行公布的每日匯率：新台幣及主要貿易對手通貨對美元匯率（1993 年起）。
        為當日 16:00 銀行間即期交易匯率，適合觀察新台幣升貶與外資動向。
        央行約每月更新一次檔案，最近幾週的資料可能尚未納入。

        Args:
            start_date: 起始日期 YYYYMMDD（選填）。未指定時回傳資料中最近 10 個交易日
            end_date: 結束日期 YYYYMMDD（選填，預設到最新）。區間最多回傳 120 個交易日
            currency: 幣別關鍵字（選填），例如 "新台幣"、"NTD"、"JPY"、"人民幣"；可用逗號分隔多個

        Returns:
            每日各幣別匯率（標示方向，例如 NTD/USD＝1 美元兌多少新台幣、USD/EUR＝1 歐元兌多少美元）
        """
        resp = _client.fetch_json(CBC_FX_URL, params={"FileName": CBC_FX_FILE}, timeout=60, cache_ttl=CBC_CACHE_TTL)
        data = (resp or {}).get("data") or {}
        columns = [c.get("data", "").strip() for c in (data.get("structure") or {}).get("Table1", [])]
        rows = data.get("dataSets") or []
        if not columns or not rows:
            return "目前沒有央行匯率資料。"

        keys = [k.strip().upper() for k in currency.split(",") if k.strip()]
        picked = [i for i, c in enumerate(columns) if not keys or any(k in c.upper() for k in keys)]
        if not picked:
            return f"查無幣別「{currency}」，可用幣別: {', '.join(columns)}"

        if start_date:
            rows = [r for r in rows if start_date <= r[0] <= (end_date or "99999999")]
        elif end_date:
            rows = [r for r in rows if r[0] <= end_date][-DEFAULT_DAYS:]
        else:
            rows = rows[-DEFAULT_DAYS:]
        if not rows:
            return f"查無 {start_date}～{end_date or '最新'} 的匯率資料（資料最新至 {data['dataSets'][-1][0]}）"
        note = ""
        if len(rows) > MAX_DAYS:
            rows = rows[-MAX_DAYS:]
            note = f"，僅顯示最後 {MAX_DAYS} 個交易日"

        last_updated = (resp.get("meta") or {}).get("last_updated", "")
        lines = [f"【中央銀行 主要貿易對手通貨對美元匯率】（資料更新至 {last_updated}{note}）"]
        for r in rows:
            cells = [f"{columns[i]}:{r[i + 1]}" for i in picked if i + 1 < len(r) and r[i + 1] != "-"]
            lines.append(f"{r[0][:4]}-{r[0][4:6]}-{r[0][6:]} | " + " | ".join(cells))
        return "\n".join(lines)
