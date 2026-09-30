"""Multi-period financial statements (綜合損益表／資產負債表／現金流量表) from MOPS.

The TWSE OpenAPI statements behind get_company_income_statement / get_company_balance_sheet
(t187ap06/t187ap07) only carry the latest reported quarter and have no cash-flow statement
at all. MOPS's t164sb03/04/05 accept any past year+quarter and return every line item for
that quarter next to the prior-year comparison columns.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.mops import mops_post, flatten_titles, to_roc_year

# statement key → (MOPS api name, display name)
STATEMENTS = {
    "income": ("t164sb04", "綜合損益表"),
    "balance": ("t164sb03", "資產負債表"),
    "cashflow": ("t164sb05", "現金流量表"),
}


def format_statement(result: dict, code: str, statement_name: str) -> str:
    """Render a t164sb0x ``result`` generically from its own headers.

    Line items differ by industry (a bank's income statement has 利息淨收益 instead of
    營業毛利), so nothing here refers to a specific account name: every row is printed
    against the column labels MOPS itself sends.
    """
    columns = flatten_titles(result.get("titles", []))
    rows = result.get("reportList") or []
    value_columns = columns[1:]  # columns[0] is 會計項目

    name = result.get("companyAbbreviation", "")
    unit = "新台幣仟元；每股盈餘為元" if statement_name == STATEMENTS["income"][1] else "新台幣仟元"
    report_type = result.get("reportType", "")
    lines = [
        f"【{name}({code}) {report_type}{statement_name}】（單位：{unit}）",
        "欄位: " + " | ".join(value_columns),
        "",
    ]
    for row in rows:
        if not row:
            continue
        item = str(row[0]).replace("　", " ").strip()
        values = [str(v).strip() for v in row[1:]]
        if not any(values):
            lines.append(f"〔{item}〕")
            continue
        lines.append(f"{item}: " + " | ".join(v or "-" for v in values))
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS multi-period financial statement tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _query(statement: str, code: str, year: str, season: int) -> str:
        api_name, statement_name = STATEMENTS[statement]
        if season not in (1, 2, 3, 4):
            return "season 必須是 1～4"
        roc_year = to_roc_year(year)
        result = mops_post(_client, api_name, {
            "companyId": code.strip(),
            "dataType": "2",
            "year": str(roc_year),
            "season": str(season),
            "subsidiaryCompanyId": "",
        })
        if not result or not result.get("reportList"):
            return f"查無 {code} 在 {roc_year} 年第 {season} 季的{statement_name}（可能尚未公告，或代號有誤）"
        return format_statement(result, code.strip(), statement_name)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_income_statement_history(code: str, year: str, season: int) -> str:
        """查詢上市櫃公司「任意歷史季度」的綜合損益表（公開資訊觀測站）。
        與 get_company_income_statement（OpenAPI，僅最新一季）不同，可回溯查詢過去任一年季，
        並附上去年同期與年初至今累計的比較欄位。支援一般業、金融業等各產業格式。

        Args:
            code: 股票代號，例如 "2330"（上市、上櫃、興櫃皆可）
            year: 年度，西元（"2025"）或民國（"114"）皆可
            season: 季別 1～4

        Returns:
            每個會計項目在「當季、去年同季、今年累計、去年累計」的金額與占營收百分比，
            含營收、毛利、營業利益、稅後淨利、EPS 等
        """
        return _query("income", code, year, season)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_balance_sheet_history(code: str, year: str, season: int) -> str:
        """查詢上市櫃公司「任意歷史季度」的資產負債表（公開資訊觀測站）。
        與 get_company_balance_sheet（OpenAPI，僅最新一季）不同，可回溯查詢過去任一年季，
        並附上前一年底與去年同期的比較欄位。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可
            season: 季別 1～4

        Returns:
            每個會計項目（流動資產、負債、權益等）在各比較日期的金額與占總資產百分比
        """
        return _query("balance", code, year, season)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_cash_flow_history(code: str, year: str, season: int) -> str:
        """查詢上市櫃公司「任意歷史季度」的現金流量表（公開資訊觀測站）。
        TWSE OpenAPI 沒有現金流量表，此工具是唯一來源。金額為年初至該季末的累計數，
        並附上去年同期累計比較。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可
            season: 季別 1～4（第 4 季即全年）

        Returns:
            營業、投資、籌資活動現金流量各項目，含折舊攤銷、資本支出（取得不動產廠房及設備）、
            發放現金股利、期末現金餘額等
        """
        return _query("cashflow", code, year, season)
