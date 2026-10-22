"""Financial statements (綜合損益表／資產負債表／現金流量表) from MOPS, latest or any past quarter.

These replace the TWSE OpenAPI t187ap06/t187ap07 tools, which only carried the latest
quarter, needed a separate 公發公司 endpoint and six industry variants, and had no cash-flow
statement at all. MOPS's t164sb03/04/05 cover listed, OTC, emerging and public companies of
every industry, for the latest quarter or any past one; ``sources.mops.financial_statements`` reads them.
"""

from typing import Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.mops.financial_statements import FinancialStatement, Kind, financial_statement
from utils import TWSEAPIClient, plain, printed
from toolkit import handle_api_errors
from utils.mops import to_roc_year

STATEMENTS = {"income": "綜合損益表", "balance": "資產負債表", "cashflow": "現金流量表"}


def format_statement(statement: FinancialStatement, code: str, statement_name: str) -> str:
    """Render a statement against the column labels MOPS itself sends.

    Line items differ by industry (a bank's income statement has 利息淨收益 instead of
    營業毛利), so nothing here refers to a specific account name.
    """
    unit = "新台幣仟元；每股盈餘為元" if statement_name == STATEMENTS["income"] else "新台幣仟元"
    lines = [
        f"【{statement.name}({code}) {statement.report_type}{statement_name}】（單位：{unit}）",
        "欄位: " + " | ".join(statement.columns),
        "",
    ]
    # MOPS prints amounts with thousands separators and percentages without (-1362.67)
    shown = [plain if column.endswith(" %") else printed for column in statement.columns]
    for line in statement.lines:
        if line.is_heading:
            lines.append(f"〔{line.item}〕")
            continue
        lines.append(f"{line.item}: " + " | ".join(show(v, "-") for show, v in zip(shown, line.values, strict=True)))
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register MOPS financial statement tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _query(kind: Kind, code: str, year: str, season: int) -> str:
        statement_name = STATEMENTS[kind]
        code = code.strip()
        if not year and not season:
            roc_year = None
            period = "最新一季"
        elif not year or season not in (1, 2, 3, 4):
            raise ToolError("請同時指定 year 與 season（1～4），或兩者都留空查詢最新一季")
        else:
            roc_year = to_roc_year(year)
            period = f"{roc_year} 年第 {season} 季"
        statement = financial_statement(_client, kind, code, roc_year, season)
        if statement is None:
            return f"查無 {code} 在{period}的{statement_name}（可能尚未公告，或代號有誤）"
        return format_statement(statement, code, statement_name)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_income_statement(code: str, year: str = "", season: int = 0) -> str:
        """查詢公司綜合損益表（公開資訊觀測站）：預設最新一季，也可指定任意歷史季度。
        上市、上櫃、興櫃、公開發行公司皆可，自動採用該公司產業（一般業、金融、保險…）的報表格式。
        附去年同季與年初至今累計的比較欄位。

        回傳：每個會計項目在「當季、去年同季、今年累計、去年累計」的金額與占營收百分比，
        含營收（營業收入）、毛利、營業利益、稅後淨利、EPS（每股盈餘）等

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可；留空＝最新一季
            season: 季別 1～4；留空（0）＝最新一季。指定 year 時必填
        """
        return _query("income", code, year, season)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_balance_sheet(code: str, year: str = "", season: int = 0) -> str:
        """查詢公司資產負債表（公開資訊觀測站）：預設最新一季，也可指定任意歷史季度。
        上市、上櫃、興櫃、公開發行公司皆可，自動採用該公司產業的報表格式。
        附前一年底與去年同期的比較欄位。

        回傳：每個會計項目（流動資產、負債、權益（股東權益）等）在各比較日期的金額與占總資產百分比

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可；留空＝最新一季
            season: 季別 1～4；留空（0）＝最新一季。指定 year 時必填
        """
        return _query("balance", code, year, season)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_cash_flow_statement(code: str, year: str = "", season: int = 0) -> str:
        """查詢公司現金流量表（公開資訊觀測站）：預設最新一季，也可指定任意歷史季度。
        金額為年初至該季末的累計數，並附去年同期累計比較。

        回傳：營業、投資、籌資活動現金流量各項目，含折舊攤銷、資本支出（取得不動產廠房及設備）、
        發放現金股利、期末現金餘額等（營業活動現金流量減資本支出即自由現金流）

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可；留空＝最新一季
            season: 季別 1～4（第 4 季即全年）；留空（0）＝最新一季。指定 year 時必填
        """
        return _query("cashflow", code, year, season)
