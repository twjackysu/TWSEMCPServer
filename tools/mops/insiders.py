"""Directors' / officers' shareholdings (董監事持股餘額) and insiders' monthly holding changes
(內部人持股異動) from MOPS, latest month or any past month.

stapap1 replaces the OpenAPI /opendata/t187ap11_L (listed) and t187ap11_P (public) tools:
on 2026-09-29 every row of ten sampled companies (5 listed, 5 public) matched, and stapap1
also covers OTC / emerging companies, past months and the per-category totals.
query6_1 (monthly changes: shares bought/sold on market, other changes, pledges, trusts)
has no OpenAPI counterpart; t187ap12_L / t187ap13_L are daily pre-transfer filings, a
different disclosure.
"""

from typing import Optional, Tuple
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sources.mops.insiders import board_holdings, insider_changes
from utils import TWSEAPIClient, cap_rows, printed
from toolkit import handle_api_errors
from utils.mops import to_roc_year

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


def period(year: str, month: str) -> Tuple[Optional[int], Optional[int]]:
    """(ROC year, month) to query, or (None, None) for the latest month; ToolError when only one is given."""
    if not year and not month:
        return None, None
    if not year or not month:
        raise ToolError("請同時指定 year 與 month，或兩者都留空查詢最新月份")
    m = int(month)
    if not 1 <= m <= 12:
        raise ToolError("month 必須是 1～12")
    return to_roc_year(year), m


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_board_shareholdings(code: str, year: str = "", month: str = "") -> str:
        """查詢公司董事、監察人、經理人及大股東的持股與設質（質押）明細（公開資訊觀測站）：預設最新月份，
        也可查過去月份。上市、上櫃、興櫃、公發公司皆可。附各類董監持股合計與設質比例。

        回傳：每位內部人的職稱、姓名、選任時持股、目前持股、設質股數與比例，
        配偶未成年子女及利用他人名義持有部份，以及董監持股合計

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元或民國（選填；與 month 同時留空＝最新月份）
            month: 月份 1～12（選填）
        """
        report = board_holdings(_client, code.strip(), *period(year.strip(), month.strip()))
        if report is None:
            return f"查無 {code} 的董監事持股資料（代號可能有誤，或該月份尚未申報）"

        name = report.name or code
        yymm = report.yymm
        label = f"民國{yymm[:-2]}年{yymm[-2:]}月" if len(yymm) >= 4 else ""
        lines = [f"【{name}({code}) 董監事持股餘額明細 {label}】", "欄位: " + " | ".join(report.columns), ""]
        shown, cap_note = cap_rows(report.holdings, MAX_OUTPUT_ROWS)
        for h in shown:
            lines.append(f"{h.title} {h.name}: " + " | ".join(h.values))
        if cap_note:
            lines.append(cap_note.lstrip("，"))

        if report.totals:
            lines.append("\n持股合計（持股 | 設質股數 | 設質比例）:")
            for key, total_label in TOTAL_LABELS.items():
                if key in report.totals:
                    lines.append(f"  {total_label}: " + " | ".join(report.totals[key]))
        lines += [text for text in (report.note, report.reason) if text]
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_insider_holding_changes(code: str, year: str = "", month: str = "",
                                            only_changed: bool = True) -> str:
        """查詢公司內部人（董監、經理人、持股10%以上大股東及其配偶子女）的每月持股異動
        （公開資訊觀測站）：預設最新月份，也可查過去月份。可看出誰在集中市場買賣、設質或解質。

        回傳：每位內部人的身份別、姓名、持股種類、上月持股、本月實際持股，
        以及本月增加／減少（集中市場、其他原因、私募、信託、設質／解質）中不為零的項目

        Args:
            code: 股票代號，例如 "2330"
            year: 年度，西元或民國（選填；與 month 同時留空＝最新月份）
            month: 月份 1～12（選填）
            only_changed: 只列本月有增減的申報人（預設 True）；False 則列出全部申報人
        """
        report = insider_changes(_client, code.strip(), *period(year.strip(), month.strip()))
        if report is None:
            return f"查無 {code} 的內部人持股異動資料（代號可能有誤，或該月份尚未申報）"

        name = report.name or code
        rows = report.changes
        changed = [c for c in rows if c.changed]
        lines = [f"【{name}({code}) 內部人持股異動 民國{report.year}年{report.month}月】"
                 f"（共 {len(rows)} 位申報人，本月有異動 {len(changed)} 位）\n"]
        if only_changed and not changed:
            return lines[0] + "本月沒有任何內部人持股異動（only_changed=False 可列出全部申報人目前持股）"
        shown, cap_note = cap_rows(changed if only_changed else rows, MAX_OUTPUT_ROWS)
        for c in shown:
            moves = [f"{title}:{printed(shares)}" for title, shares in c.moves if shares]
            who = f"{c.identity} {c.name}".strip()
            head = (f"{who}（{c.share_type}）| 上月持股:{printed(c.last_month)} → 本月持股:{printed(c.this_month)} | "
                    f"累計設質:{printed(c.pledged)}")
            lines.append(head + (" | " + " | ".join(moves) if moves else ""))
        if cap_note:
            lines.append(cap_note.lstrip("，"))
        return "\n".join(lines)
