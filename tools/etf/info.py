"""ETF basic information, for every issuer and both markets.

Three sources, each covering a different part:
- SITCA ETF zone etf_info2 (utils/sitca.py): 經理公司, 成立日, 分類, 追蹤指數, 配息 for ~340
  domestic ETFs of every issuer, TWSE- and TPEx-listed alike.
- TWSE openapi t187ap47_L 基金基本資料彙總表: TWSE-listed funds only, but with 經理人, 保管機構,
  上市日期, 發行單位數 and also the futures-trust / foreign-currency codes SITCA lacks.
- TPEx website ETF/list + ETF/detail: TPEx-listed ETFs, with 管理費 / 保管費 and trading rules.

This replaces get_fund_basic_info (t187ap47_L only): on 2026-10-14 every t187ap47_L code is
listed here and a single-code lookup shows all of its fields.
"""

import html
import json
import re
from typing import Dict, List, Optional

from fastmcp import FastMCP
from utils import TWSEAPIClient, format_list_response, DEFAULT_DISPLAY_LIMIT
from toolkit import handle_api_errors
from utils.sitca import SITCA_CACHE_TTL, SITCA_HEADERS, available_months, query_rows

FUND_BASIC_ENDPOINT = "/opendata/t187ap47_L"
TPEX_ETF_LIST_URL = "https://www.tpex.org.tw/www/zh-tw/ETF/list"
TPEX_ETF_DETAIL_URL = "https://www.tpex.org.tw/www/zh-tw/ETF/detail"
TPEX_ETF_TYPES = ("domestic", "foreign", "bond")
# t187ap47_L metadata fields not worth echoing.
_SKIP_TWSE_FIELDS = {"出表日期"}
_TAG_RE = re.compile(r"<[^>]+>")


def _fmt_ymd(text: str) -> str:
    """20030625 (SITCA) or 0920630 (ROC, t187ap47_L) → 2003-06-25; anything else unchanged."""
    text = html.unescape(str(text)).strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if re.fullmatch(r"\d{7}", text):
        return f"{int(text[:3]) + 1911}-{text[3:5]}-{text[5:]}"
    return text


def sitca_info_records(rows: List[List[str]]) -> List[Dict[str, str]]:
    """SITCA etf_info2 rows → dicts keyed by its header, funds without a 證券代號 dropped."""
    if not rows:
        return []
    header = rows[0]
    records = [dict(zip(header, r)) for r in rows[1:]]
    return [r for r in records if r.get("證券代號", "-") not in ("", "-")]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register ETF basic-info tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _sitca_info() -> List[Dict[str, str]]:
        ym = available_months(_client, "etf_info.aspx")[0]
        return sitca_info_records(query_rows(_client, "etf_info2.aspx", ym))

    def _tpex_post(url: str, form: Dict[str, str]) -> dict:
        body = _client.fetch_bytes(url, data={**form, "response": "json"}, method="POST",
                                   headers=SITCA_HEADERS, timeout=60, cache_ttl=SITCA_CACHE_TTL)
        return json.loads(body.decode("utf-8"))

    def _tpex_type(code: str) -> Optional[str]:
        for etf_type in TPEX_ETF_TYPES:
            table = (_tpex_post(TPEX_ETF_LIST_URL, {"type": etf_type}).get("tables") or [{}])[0]
            if any(row and row[0].strip() == code for row in table.get("data") or []):
                return etf_type
        return None

    def _tpex_detail_lines(code: str) -> List[str]:
        etf_type = _tpex_type(code)
        if etf_type is None:
            return []
        lines = []
        for table in _tpex_post(TPEX_ETF_DETAIL_URL, {"type": etf_type, "code": code}).get("tables") or []:
            fields, data = table.get("fields") or [], table.get("data") or []
            if not data or len(fields) < 2:
                continue  # the PCF table is only a link to the issuer's site
            for name, value in zip(fields, data[0]):
                value = " ".join(_TAG_RE.sub(" ", str(value)).split())
                if value and name not in ("證券代號",):
                    lines.append(f"{name}: {value}")
        return lines

    def _single(code: str) -> str:
        sitca = next((r for r in _sitca_info() if r["證券代號"] == code), None)
        twse = next((r for r in _client.fetch_data(FUND_BASIC_ENDPOINT) if r.get("基金代號", "").strip() == code), None)
        tpex_lines = _tpex_detail_lines(code)
        if not (sitca or twse or tpex_lines):
            return f"查無 ETF 代號 {code} 的基本資料（請確認代號，例如 0050、00679B）"

        name = (sitca or {}).get("證券簡稱") or html.unescape((twse or {}).get("基金簡稱", "")) or code
        parts = [f"【{code} {name} ETF 基本資料】"]
        if sitca:
            parts.append("\n▍投信投顧公會")
            for key in ("經理公司", "基金名稱", "基金成立日期", "分類", "追蹤指數", "是否有發行 配息級別"):
                value = sitca.get(key, "")
                if value and value != "-":
                    label = "配息" if key.startswith("是否有發行") else key
                    parts.append(f"{label}: {_fmt_ymd(value) if key == '基金成立日期' else value}")
        if twse:
            parts.append("\n▍證交所基金基本資料")
            for key, value in twse.items():
                if key not in _SKIP_TWSE_FIELDS and key != "基金代號" and str(value).strip():
                    parts.append(f"{key}: {_fmt_ymd(value)}")
        if tpex_lines:
            parts.append("\n▍櫃買中心商品規格")
            parts.extend(tpex_lines)
        return "\n".join(parts)

    @mcp.tool
    @handle_api_errors()
    def get_etf_info(code: str = "", issuer: str = "", category: str = "", keyword: str = "",
                     limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢 ETF 基本資料，涵蓋所有投信、上市與上櫃（含債券 ETF、主動式 ETF）。
        指定 code 時列出單一 ETF 的完整資料：經理公司、成立／上市日、分類、追蹤指數、配息頻率、
        經理人、保管機構；上櫃 ETF 另有管理費、保管費與交易規則。
        不指定 code 時列出 ETF 清單，可用 issuer／category／keyword 篩選。

        回傳：單一 ETF：各來源的基本資料；清單：代號、簡稱、經理公司、分類、追蹤指數、成立日

        Args:
            code: ETF 證券代號，例如 "0050"、"00679B"、"00981A"（選填，留空＝列清單）
            issuer: 投信名稱關鍵字，例如 "元大"、"國泰"（列清單時篩選）
            category: 分類關鍵字，例如 "債券"、"國外"、"槓桿"、"反向"、"上櫃"（列清單時篩選）
            keyword: 代號、名稱或追蹤指數關鍵字，例如 "高股息"、"S&P"（列清單時篩選）
            limit: 清單筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        code = code.strip().upper()
        if code:
            return _single(code)

        records = [
            {"代號": r["證券代號"], "簡稱": r.get("證券簡稱", ""), "經理公司": r.get("經理公司", ""),
             "分類": r.get("分類", ""), "追蹤指數": r.get("追蹤指數", ""),
             "成立日": _fmt_ymd(r.get("基金成立日期", "")), "名稱": r.get("基金名稱", "")}
            for r in _sitca_info()
        ]
        known = {r["代號"] for r in records}
        # Futures-trust and foreign-currency codes are not SITCA funds; t187ap47_L still has them.
        for r in _client.fetch_data(FUND_BASIC_ENDPOINT):
            fund_code = r.get("基金代號", "").strip()
            if fund_code and fund_code not in known:
                records.append({"代號": fund_code, "簡稱": html.unescape(r.get("基金簡稱", "")), "經理公司": "",
                                "分類": r.get("基金類型", ""), "追蹤指數": html.unescape(r.get("標的指數/追蹤指數名稱", "")),
                                "成立日": _fmt_ymd(r.get("成立日期", "")), "名稱": html.unescape(r.get("基金中文名稱", ""))})

        def match(r: Dict[str, str]) -> bool:
            if issuer and issuer not in r["經理公司"] and issuer not in r["名稱"]:
                return False
            if category and category not in r["分類"]:
                return False
            text = " ".join((r["代號"], r["簡稱"], r["名稱"], r["追蹤指數"]))
            return not keyword or keyword.lower() in text.lower()

        records = sorted((r for r in records if match(r)), key=lambda r: r["代號"])

        def fmt(r: Dict[str, str]) -> str:
            line = f"- {r['代號']} {r['簡稱']}"
            for key in ("經理公司", "分類", "追蹤指數", "成立日"):
                if r[key]:
                    line += f" | {r[key]}"
            return line + "\n"

        return format_list_response(records, "ETF", fmt, limit, offset)
