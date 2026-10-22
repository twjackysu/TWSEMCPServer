"""MOPS t164sb03 / t164sb04 / t164sb05: 資產負債表 / 綜合損益表 / 現金流量表 — one company's statement for one quarter.

``POST https://mops.twse.com.tw/mops/api/<t164sb0x>`` with ``{"companyId", "dataType": "1" (latest) or "2",
"year" (ROC), "season" ("1"–"4"), "subsidiaryCompanyId": ""}``; the latest quarter still needs the empty
``year`` / ``season`` (without them MOPS answers 傳入參數異常). Reply::

    {"companyAbbreviation": "台積電", "reportType": "合併", "year": "114", "season": "2",
     "titles": [{"main": "會計項目"}, {"main": "114年第2季", "sub": [{"main": "金額"}, {"main": "%"}]},
                {"main": "113年第2季", "sub": […]}, {"main": "114年01月01日至114年06月30日", "sub": […]}, …],
     "reportList": [["營業收入合計", "933,791,869", "100.00", "673,510,177", "100.00", …],
                    ["　　推銷費用", …], ["營業費用", "", "", …], …]}

The periods depend on the statement and quarter (a balance sheet's dates, 114年度 in a 4th quarter's cash flow),
and the line items on the industry (a bank has 利息淨收益 instead of 營業毛利), so neither is fixed here: the columns
are the flattened titles after 會計項目, as published. 會計項目 is indented with full-width spaces; a line whose cells
are all empty is a section heading. Cells are numbers ("-1,234", "-0.05", "0") or "" (EPS has no %): amounts with
thousands separators, percentages without ("-1362.67", 國泰金's 兌換損益 in 114Q2). Amounts in 新台幣仟元, EPS in 元,
% of revenue / total assets. Same titles checked 2013–2026 (IFRS; 2010 answers 406) for
manufacturers, a bank, a financial holding, a securities firm, a leasing company, 興櫃 and OTC companies.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Literal, Optional, Tuple

from utils.api_client import TWSEAPIClient
from utils.errors import UpstreamFormatError
from utils.mops import flatten_titles, mops_post
from utils.parse import decimal_or_none

from ..columns import column_index

Kind = Literal["income", "balance", "cashflow"]  # API_NAMES
API_NAMES: Dict[Kind, str] = {"income": "t164sb04", "balance": "t164sb03", "cashflow": "t164sb05"}
ITEM = "會計項目"


@dataclass(frozen=True)
class StatementLine:
    item: str                              # 會計項目 without its indentation ("推銷費用")
    level: int                             # indentation: the full-width spaces MOPS puts before it (0 = none)
    values: Tuple[Optional[Decimal], ...]  # one per FinancialStatement.columns; None where the cell is empty

    @property
    def is_heading(self) -> bool:
        """A section title such as 營業費用 or 流動資產: every cell empty."""
        return all(v is None for v in self.values)


@dataclass(frozen=True)
class FinancialStatement:
    name: str                  # companyAbbreviation
    report_type: str           # reportType as published ("合併")
    columns: Tuple[str, ...]   # each value column's flattened title: "114年第2季 金額", "114年第2季 %", "114年度 金額"
    lines: List[StatementLine]


def _value(cell, api_name: str) -> Optional[Decimal]:
    text = str(cell).strip()
    if not text:
        return None
    value = decimal_or_none(text)
    if value is None:
        raise UpstreamFormatError(f"{api_name} 數字格式已變更：{text!r}")
    return value


def financial_statement(client: TWSEAPIClient, kind: Kind, code: str, roc_year: Optional[int] = None,
                        season: Optional[int] = None) -> Optional[FinancialStatement]:
    """``code``'s ``kind`` statement for ``season`` of ROC year ``roc_year``, or the latest quarter's without a year;
    None when MOPS has none (not yet published, or before IFRS). Raises ``UpstreamFormatError`` if 會計項目 is gone
    or a row does not match the titles."""
    api_name = API_NAMES[kind]
    if roc_year is None:
        body = {"companyId": code, "dataType": "1", "year": "", "season": "", "subsidiaryCompanyId": ""}
    else:
        body = {"companyId": code, "dataType": "2", "year": str(roc_year), "season": str(season),
                "subsidiaryCompanyId": ""}
    result = mops_post(client, api_name, body)
    if not result or not result.get("reportList"):
        return None
    names = flatten_titles(result.get("titles") or [])
    item = column_index(names, (ITEM,), api_name)[ITEM]
    lines = []
    for r in result["reportList"]:
        if not isinstance(r, list) or len(r) != len(names):
            raise UpstreamFormatError(f"{api_name} 資料列與 titles 對不上（{len(names)} 欄）：{str(r)[:200]}")
        raw = str(r[item])
        lines.append(StatementLine(
            item=raw.replace("　", " ").strip(),
            level=len(raw) - len(raw.lstrip("　")),
            values=tuple(_value(c, api_name) for i, c in enumerate(r) if i != item),
        ))
    return FinancialStatement(
        name=str(result.get("companyAbbreviation") or "").strip(),
        report_type=str(result.get("reportType") or "").strip(),
        columns=tuple(n for i, n in enumerate(names) if i != item),
        lines=lines,
    )
