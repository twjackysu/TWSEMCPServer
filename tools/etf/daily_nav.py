"""ETF units outstanding, estimated NAV and premium/discount — today, every issuer.

Source: TWSE MIS "ETF發行單位變動及淨值揭露專區" feed mis.twse.com.tw/stock/data/all_etf.txt.
Each issuer pushes its ETFs there in the format TWSE specifies (介接格式說明 v1.5): a=代號,
b=名稱, c=已發行受益權單位數, d=與前日單位數差異, e=成交價, f=預估淨值, g=預估折溢價(%),
h=前一營業日淨值 ("未結出" before it is struck), i=資料日期, j=資料時間, k=標的類型.
~360 ETFs in one request, TWSE- and TPEx-listed, futures-trust ETFs included. Values come as
numbers or strings depending on the issuer, so everything goes through _num.
"""

from typing import Any, Dict, List, Literal, Optional

from fastmcp import FastMCP
from utils import TWSEAPIClient
from toolkit import bounded, handle_api_errors

MIS_ALL_ETF_URL = "https://mis.twse.com.tw/stock/data/all_etf.txt"
# Issuers refresh the estimated NAV every ~15 s during trading hours.
MIS_ETF_CACHE_TTL = 30
MAX_LIST = 100

SortBy = Literal["scale", "premium", "discount", "creation", "redemption"]  # SORTS
SORTS = {
    "scale": ("規模", lambda r: r["scale"] or 0, True),
    "premium": ("溢價", lambda r: r["premium"] if r["premium"] is not None else float("-inf"), True),
    "discount": ("折價", lambda r: r["premium"] if r["premium"] is not None else float("inf"), False),
    "creation": ("單位數增加（淨申購）", lambda r: r["change"] or 0, True),
    "redemption": ("單位數減少（淨買回）", lambda r: r["change"] or 0, False),
}


def _num(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_all_etf(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten the per-issuer groups into one row per ETF."""
    rows = []
    for group in payload.get("a1") or []:
        for item in group.get("msgArray") or []:
            code = str(item.get("a", "")).strip()
            if not code:
                continue
            units, prior_nav, est_nav = _num(item.get("c")), _num(item.get("h")), _num(item.get("f"))
            nav = prior_nav if prior_nav is not None else est_nav
            rows.append({
                "code": code, "name": str(item.get("b", "")).strip(),
                "units": units, "change": _num(item.get("d")), "price": _num(item.get("e")),
                "est_nav": est_nav, "premium": _num(item.get("g")), "prior_nav": prior_nav,
                "prior_nav_text": str(item.get("h", "")).strip(),
                "date": str(item.get("i", "")).strip(), "time": str(item.get("j", "")).strip(),
                "scale": units * nav if units is not None and nav is not None else None,
            })
    return rows


def _fmt(value: Optional[float], digits: int = 2, signed: bool = False) -> str:
    if value is None:
        return "-"
    return f"{value:+,.{digits}f}" if signed else f"{value:,.{digits}f}"


def format_row(r: Dict[str, Any]) -> str:
    prior = _fmt(r["prior_nav"], 4) if r["prior_nav"] is not None else (r["prior_nav_text"] or "-")
    scale = f"{r['scale'] / 1e8:,.1f} 億元" if r["scale"] is not None else "-"
    return (
        f"{r['code']} {r['name']} | 市價 {_fmt(r['price'])} | 預估淨值 {_fmt(r['est_nav'], 4)} | "
        f"折溢價 {_fmt(r['premium'], 2, True)}% | 前日淨值 {prior} | "
        f"已發行單位數 {_fmt(r['units'], 0)}（較前日 {_fmt(r['change'], 0, True)}）| 規模約 {scale}"
    )


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the ETF daily NAV / premium tool."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_etf_daily_nav(code: str = "", sort_by: SortBy = "scale", limit: bounded(1, MAX_LIST) = 30) -> str:
        """查詢 ETF 當日已發行單位數（較前日增減＝淨申購／買回）、預估淨值、折溢價與規模，
        涵蓋所有投信、上市與上櫃（含債券 ETF、期貨 ETF）。盤中為投信即時預估淨值（約 15 秒更新），
        收盤後為當日最終數字。可用來檢查是否溢價過高、哪些 ETF 正大量申購或買回。

        回傳：每檔 ETF 的市價、預估淨值、折溢價(%)、前日淨值、已發行單位數與較前日增減、
        規模估計（已發行單位數 × 前日淨值）與資料時間

        Args:
            code: ETF 代號，可用逗號查多檔，例如 "0050" 或 "0050,00878,00679B"（留空＝列排行）
            sort_by: 未指定 code 時的排序：scale（規模，預設）、premium（溢價最高）、
                discount（折價最深）、creation（單位數增加最多）、redemption（單位數減少最多）
            limit: 排行筆數（預設 30，最多 100）
        """
        rows = parse_all_etf(_client.fetch_json(MIS_ALL_ETF_URL, cache_ttl=MIS_ETF_CACHE_TTL))
        if not rows:
            return "目前查無 ETF 淨值揭露資料"
        latest = max(r["date"] for r in rows)

        codes = [c.strip().upper() for c in code.split(",") if c.strip()]
        if codes:
            by_code = {r["code"]: r for r in rows}
            found = [by_code[c] for c in codes if c in by_code]
            missing = [c for c in codes if c not in by_code]
            if not found:
                return f"查無 ETF 代號 {', '.join(missing)} 的淨值揭露資料"
            lines = [f"【ETF 單位數與淨值】資料日期 {latest[:4]}-{latest[4:6]}-{latest[6:]}\n"]
            lines += [f"{format_row(r)} | 更新 {r['time']}" for r in found]
            if missing:
                lines.append(f"\n查無：{', '.join(missing)}")
            return "\n".join(lines)

        label, key, reverse = SORTS[sort_by]
        ranked = sorted(rows, key=key, reverse=reverse)[:limit]
        lines = [f"【ETF {label}排行】資料日期 {latest[:4]}-{latest[4:6]}-{latest[6:]}（共 {len(rows)} 檔，列出前 {len(ranked)} 檔）\n"]
        lines += [f"{i}. {format_row(r)}" for i, r in enumerate(ranked, 1)]
        return "\n".join(lines)
