"""Financial statements (綜合損益表／資產負債表／現金流量表) from MOPS, latest or any past quarter.

These replace the TWSE OpenAPI t187ap06/t187ap07 tools, which only carried the latest
quarter, needed a separate 公發公司 endpoint and six industry variants, and had no cash-flow
statement at all. MOPS's t164sb03/04/05 cover listed, OTC, emerging and public companies of
every industry, for the latest quarter (``dataType`` "1") or any past one ("2").
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
    """Register MOPS financial statement tools."""
    _client = client or TWSEAPIClient.get_instance()

    def _query(statement: str, code: str, year: str, season: int) -> str:
        api_name, statement_name = STATEMENTS[statement]
        code = code.strip()
        if not year and not season:
            # 最新一季：dataType=1 仍須帶空的 year/season，少了會回「傳入參數異常」
            body = {"companyId": code, "dataType": "1", "year": "", "season": "", "subsidiaryCompanyId": ""}
            period = "最新一季"
        elif not year or season not in (1, 2, 3, 4):
            return "請同時指定 year 與 season（1～4），或兩者都留空查詢最新一季"
        else:
            roc_year = to_roc_year(year)
            body = {"companyId": code, "dataType": "2", "year": str(roc_year), "season": str(season),
                    "subsidiaryCompanyId": ""}
            period = f"{roc_year} 年第 {season} 季"
        result = mops_post(_client, api_name, body)
        if not result or not result.get("reportList"):
            return f"查無 {code} 在{period}的{statement_name}（可能尚未公告，或代號有誤）"
        return format_statement(result, code, statement_name)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_income_statement(code: str, year: str = "", season: int = 0) -> str:
        """查詢公司綜合損益表（公開資訊觀測站）：預設最新一季，也可指定任意歷史季度。
        上市、上櫃、興櫃、公開發行公司皆可，自動採用該公司產業（一般業、金融、保險…）的報表格式。
        附去年同季與年初至今累計的比較欄位。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可；留空＝最新一季
            season: 季別 1～4；留空（0）＝最新一季。指定 year 時必填

        Returns:
            每個會計項目在「當季、去年同季、今年累計、去年累計」的金額與占營收百分比，
            含營收、毛利、營業利益、稅後淨利、EPS 等
        """
        return _query("income", code, year, season)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_balance_sheet(code: str, year: str = "", season: int = 0) -> str:
        """查詢公司資產負債表（公開資訊觀測站）：預設最新一季，也可指定任意歷史季度。
        上市、上櫃、興櫃、公開發行公司皆可，自動採用該公司產業的報表格式。
        附前一年底與去年同期的比較欄位。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可；留空＝最新一季
            season: 季別 1～4；留空（0）＝最新一季。指定 year 時必填

        Returns:
            每個會計項目（流動資產、負債、權益等）在各比較日期的金額與占總資產百分比
        """
        return _query("balance", code, year, season)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_cash_flow_statement(code: str, year: str = "", season: int = 0) -> str:
        """查詢公司現金流量表（公開資訊觀測站）：預設最新一季，也可指定任意歷史季度。
        金額為年初至該季末的累計數，並附去年同期累計比較。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元（"2025"）或民國（"114"）皆可；留空＝最新一季
            season: 季別 1～4（第 4 季即全年）；留空（0）＝最新一季。指定 year 時必填

        Returns:
            營業、投資、籌資活動現金流量各項目，含折舊攤銷、資本支出（取得不動產廠房及設備）、
            發放現金股利、期末現金餘額等
        """
        return _query("cashflow", code, year, season)
