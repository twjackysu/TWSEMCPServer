"""Dividend distribution (股利分派情形) from MOPS t05st09_2, recent or any span of years.

Replaces the OpenAPI t187ap45_L tool, which only listed the latest board resolutions of
listed companies; this covers OTC/emerging/public companies and quarterly dividends too.
"""

import re
from datetime import date
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.mops import mops_post, leaf_titles, to_roc_year

MAX_YEARS = 10

# Leaf column names the tool prints, looked up by name rather than position.
# tests/e2e/test_mops_api.py asserts they are still present.
KEY_COLUMNS = [
    "決議（擬議）進度",
    "股利所屬年（季）度",
    "董事會決議（擬議）股利分派日",
    "股東會日期",
    "本期淨利（淨損）（元）",
    "盈餘分配之現金股利（元/股）",
    "法定盈餘公積發放之現金（元/股）",
    "資本公積發放之現金（元/股）",
    "盈餘轉增資配股（元/股）",
    "法定盈餘公積轉增資配股（元/股）",
    "資本公積轉增資配股（元/股）",
]

# queryType: 1 = 董事會決議（擬議）分配股利年度, 2 = 股利所屬年度
YEAR_TYPES = {"dividend": "2", "board": "1"}

_TAG_RE = re.compile(r"<[^>]+>")


def format_dividend_rows(section: dict, label: str) -> list:
    """Render one ``commonStock`` / ``specialStock`` section as text lines."""
    titles = leaf_titles(section.get("titles", []))
    rows = section.get("data") or []
    if not rows:
        return []
    index = {name: i for i, name in enumerate(titles)}
    lines = [f"〔{label}〕"]
    for row in rows:
        parts = []
        # 特別股多一欄「特別股代號/名稱」，放在最前面
        if "特別股代號/名稱" in index:
            parts.append(str(row[index["特別股代號/名稱"]]))
        for col in KEY_COLUMNS:
            i = index.get(col)
            value = _TAG_RE.sub("", str(row[i])).strip() if i is not None and i < len(row) else "N/A"
            parts.append(f"{col}:{value}")
        lines.append(" | ".join(parts))
    return lines


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS dividend history tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_dividend(code: str, start_year: str = "", end_year: str = "",
                             year_type: str = "dividend") -> str:
        """查詢公司股利分派（公開資訊觀測站）：預設近兩年，也可回溯多年評估配息穩定性。
        上市、上櫃、興櫃、公開發行公司皆可，季配息公司會列出每一季的股利。

        Args:
            code: 股票代號，例如 "2330"
            start_year: 起始年度，西元（"2021"）或民國（"110"）皆可；留空＝去年起
            end_year: 結束年度（選填，預設今年；有指定 start_year 時預設同 start_year）。區間最多 10 年
            year_type: "dividend"＝依股利所屬年度（預設，例如 2024 年盈餘所配的股利）；
                "board"＝依董事會決議年度

        Returns:
            每次股利分派的決議進度、所屬年（季）度、董事會決議日、股東會日期、當期淨利、
            現金股利（盈餘/法定公積/資本公積，元/股）、股票股利（元/股）
        """
        code = code.strip()
        query_type = YEAR_TYPES.get(year_type.strip().lower())
        if query_type is None:
            return "year_type 只能是 \"dividend\"（股利所屬年度）或 \"board\"（董事會決議年度）"
        this_year = date.today().year - 1911
        if start_year.strip():
            first = to_roc_year(start_year)
            last = to_roc_year(end_year) if end_year.strip() else first
        else:
            # 預設涵蓋最近一次決議：今年與去年（股利所屬年度常落後決議一年）
            first, last = this_year - 1, (to_roc_year(end_year) if end_year.strip() else this_year)
        if first > last:
            return "起始年度不可晚於結束年度"
        if last - first + 1 > MAX_YEARS:
            return f"查詢區間最多 {MAX_YEARS} 年，請縮小範圍"

        result = mops_post(_client, "t05st09_2", {
            "companyId": code,
            "dataType": "2",
            "firstYear": str(first),
            "lastYear": str(last),
            "queryType": query_type,
        })
        if not result:
            return f"查無 {code} 在民國 {first}～{last} 年的股利分派資料"

        lines = format_dividend_rows(result.get("commonStock") or {}, "普通股")
        special = result.get("specialStock") or {}
        lines += format_dividend_rows(special, "特別股")
        if not lines:
            return f"查無 {code} 在民國 {first}～{last} 年的股利分派資料"

        name = result.get("companyAbbreviation", "")
        basis = "股利所屬年度" if query_type == "2" else "董事會決議年度"
        header = f"【{name}({code}) 股利分派歷史 民國{first}～{last}年（依{basis}）】\n"
        return header + "\n".join(lines)
