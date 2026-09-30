"""Directors' / officers' shareholdings (董監事持股餘額) and insiders' monthly holding changes
(內部人持股異動) from MOPS, latest month or any past month.

stapap1 replaces the OpenAPI /opendata/t187ap11_L (listed) and t187ap11_P (public) tools:
on 2026-09-29 every row of ten sampled companies (5 listed, 5 public) matched, and stapap1
also covers OTC / emerging companies, past months and the per-category totals.
query6_1 (monthly changes: shares bought/sold on market, other changes, pledges, trusts)
has no OpenAPI counterpart; t187ap12_L / t187ap13_L are daily pre-transfer filings, a
different disclosure.
"""

from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors, cap_rows
from utils.mops import mops_post, flatten_titles, to_roc_year

# stapap1 result.parentCompany.total → label
TOTAL_LABELS = {
    "nonIndependentDirector": "非獨立董事",
    "independentDirector": "獨立董事",
    "nonIndependentSupervisor": "非獨立監察人",
    "independentSupervisor": "獨立監察人",
    "nonIndependentDirectorSupervisor": "非獨立董監合計",
    "independentDirectorSupervisor": "獨立董監合計",
    "allDirectorSupervisor": "全體董監合計",
}
MAX_OUTPUT_ROWS = 200


def period_body(code: str, year: str, month: str) -> tuple:
    """MOPS body for the latest month (dataType 1, blank year/month) or a given month."""
    if not year and not month:
        return {"companyId": code, "dataType": "1", "year": "", "month": "", "subsidiaryCompanyId": ""}, None
    if not year or not month:
        return None, "請同時指定 year 與 month，或兩者都留空查詢最新月份"
    m = int(month)
    if not 1 <= m <= 12:
        return None, "month 必須是 1～12"
    return {"companyId": code, "dataType": "2", "year": str(to_roc_year(year)), "month": f"{m:02d}",
            "subsidiaryCompanyId": ""}, None


def _nonzero(value) -> bool:
    text = str(value).replace(",", "").replace("%", "").strip()
    try:
        return float(text) != 0
    except ValueError:
        return bool(text)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_board_shareholdings(code: str, year: str = "", month: str = "") -> str:
        """查詢公司董事、監察人、經理人及大股東的持股與設質明細（公開資訊觀測站）：預設最新月份，
        也可查過去月份。上市、上櫃、興櫃、公發公司皆可。附各類董監持股合計與設質比例。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元或民國（選填；與 month 同時留空＝最新月份）
            month: 月份 1～12（選填）

        Returns:
            每位內部人的職稱、姓名、選任時持股、目前持股、設質股數與比例，
            配偶未成年子女及利用他人名義持有部份，以及董監持股合計
        """
        body, error = period_body(code.strip(), year.strip(), month.strip())
        if error:
            return error
        result = mops_post(_client, "stapap1", body)
        parent = (result or {}).get("parentCompany") or {}
        rows = parent.get("data") or []
        if not rows:
            return f"查無 {code} 的董監事持股資料（代號可能有誤，或該月份尚未申報）"

        columns = flatten_titles(parent.get("titles", []))
        name = parent.get("companyAbbreviation") or code
        yymm = str(parent.get("yymm", ""))
        period = f"民國{yymm[:-2]}年{yymm[-2:]}月" if len(yymm) >= 4 else ""
        lines = [f"【{name}({code}) 董監事持股餘額明細 {period}】", "欄位: " + " | ".join(columns[2:]), ""]
        shown, cap_note = cap_rows(rows, MAX_OUTPUT_ROWS)
        for r in shown:
            lines.append(f"{r[0]} {r[1]}: " + " | ".join(str(v) for v in r[2:]))
        if cap_note:
            lines.append(cap_note.lstrip("，"))

        totals = parent.get("total") or {}
        if totals:
            lines.append("\n持股合計（持股 | 設質股數 | 設質比例）:")
            for key, label in TOTAL_LABELS.items():
                if key in totals:
                    lines.append(f"  {label}: " + " | ".join(totals[key]))
        for key in ("note", "reason"):
            if str(parent.get(key, "")).strip():
                lines.append(str(parent[key]).strip())
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_insider_holding_changes(code: str, year: str = "", month: str = "",
                                            only_changed: bool = True) -> str:
        """查詢公司內部人（董監、經理人、持股10%以上大股東及其配偶子女）的每月持股異動
        （公開資訊觀測站）：預設最新月份，也可查過去月份。可看出誰在集中市場買賣、設質或解質。

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元或民國（選填；與 month 同時留空＝最新月份）
            month: 月份 1～12（選填）
            only_changed: 只列本月有增減的申報人（預設 True）；False 則列出全部申報人

        Returns:
            每位內部人的身份別、姓名、持股種類、上月持股、本月實際持股，
            以及本月增加／減少（集中市場、其他原因、私募、信託、設質／解質）中不為零的項目
        """
        body, error = period_body(code.strip(), year.strip(), month.strip())
        if error:
            return error
        result = mops_post(_client, "query6_1", body)
        rows = (result or {}).get("data") or []
        if not rows:
            return f"查無 {code} 的內部人持股異動資料（代號可能有誤，或該月份尚未申報）"

        columns = flatten_titles(result.get("titles", []))
        name = result.get("companyAbbreviation") or code
        period = f"民國{result.get('year', '')}年{result.get('month', '')}月"
        changed = [r for r in rows if any(_nonzero(v) for v in r[8:18])]
        lines = [f"【{name}({code}) 內部人持股異動 {period}】（共 {len(rows)} 位申報人，本月有異動 {len(changed)} 位）\n"]
        if only_changed and not changed:
            return lines[0] + "本月沒有任何內部人持股異動（only_changed=False 可列出全部申報人目前持股）"
        shown, cap_note = cap_rows(changed if only_changed else rows, MAX_OUTPUT_ROWS)
        for r in shown:
            # r[0:3] 身份別,姓名,持股種類; r[4] 上月實際持有股數; r[8:18] 本月增加/減少 各 5 欄;
            # r[18] 本月實際自有持有股數; r[21] 截至本月底累計設質; 其餘見 columns
            moves = [f"{columns[i]}:{r[i]}" for i in range(8, min(18, len(r))) if _nonzero(r[i])]
            who = f"{r[0]} {r[1]}".strip()
            head = f"{who}（{r[2]}）| 上月持股:{r[4]} → 本月持股:{r[18]} | 累計設質:{r[21]}"
            lines.append(head + (" | " + " | ".join(moves) if moves else ""))
        if cap_note:
            lines.append(cap_note.lstrip("，"))
        return "\n".join(lines)
