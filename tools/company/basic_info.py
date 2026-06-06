"""Company basic information tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    handle_api_errors,
    has_meaningful_data,
    format_meaningful_fields_only,
    MSG_NO_DATA,
    DEFAULT_DISPLAY_LIMIT,
    format_list_response,
    create_company_tool,
    create_list_tool,
    truncate,
)


def _fmt_ownership_change(i):
    result = f"- {i.get('公司名稱', 'N/A')} ({i.get('公司代號', 'N/A')}): {i.get('經營權異動日期', 'N/A')}\n"
    desc = i.get("經營權異動說明", "")
    if desc:
        result += f"  說明: {truncate(desc)}\n"
    return result


def _fmt_cumulative_voting(i):
    result = f"- {i.get('公司名稱', 'N/A')} ({i.get('公司代號', 'N/A')}): {i.get('董監事選任方式', 'N/A')}"
    meeting_date = i.get("股東常(臨時)會日期-日期", "")
    if meeting_date:
        result += f" (股東會日期: {meeting_date})"
    return result + "\n"


def _fmt_proposal_exercise(i):
    result = f"- {i.get('公司名稱', 'N/A')} ({i.get('公司代號', 'N/A')}): 股東會 {i.get('召開股東會日期', 'N/A')}\n"
    period = i.get("股東依公司法第172條之1行使提案權-提案受理期間", "")
    if period:
        result += f"  提案受理期間: {period}\n"
    content = i.get("提案內容", "")
    if content:
        result += f"  提案內容: {truncate(content)}\n"
    return result


def _list_doc(summary: str, name_label: str, has_name: bool = True) -> str:
    lines = [summary, "", "        Args:"]
    if has_name:
        lines.append(f"            name: {name_label}（選填）")
    lines.append("            limit: 回傳筆數上限（預設 50）")
    lines.append("            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）")
    return "\n".join(lines)


# Simple list tools: fetch → optional name filter → paginate.
# (endpoint, name, summary, label, empty_data_type, filter_field, name_label, formatter)
SIMPLE_LIST_TOOLS = [
    (
        "/announcement/punish", "get_market_disposal_stocks",
        "查詢集中市場公布處置股票。", "集中市場公布處置股票", "集中市場公布處置股票",
        "Name", "股票名稱關鍵字",
        lambda i: f"- {i.get('Name', 'N/A')} ({i.get('Code', 'N/A')}): {i.get('DispositionMeasures', 'N/A')} - {i.get('ReasonsOfDisposition', 'N/A')}\n",
    ),
    (
        "/opendata/t187ap24_L", "get_companies_with_ownership_changes",
        "查詢上市公司經營權及營業範圍異(變)動專區-經營權異動公司。", "上市公司經營權異動資料", "上市公司經營權異動",
        "公司名稱", "公司名稱關鍵字", _fmt_ownership_change,
    ),
    (
        "/opendata/t187ap26_L", "get_companies_ownership_changes_business_scope",
        "查詢上市公司經營權及營業範圍異(變)動專區-經營權異動且營業範圍重大變更停止買賣公司。",
        "經營權異動且營業範圍重大變更停止買賣公司資料", "經營權異動且營業範圍重大變更停止買賣公司",
        None, None,
        lambda i: f"- {i.get('公司名稱', 'N/A')} ({i.get('公司代號', 'N/A')}): {i.get('停止買賣日期', 'N/A')}\n",
    ),
    (
        "/opendata/t187ap27_L", "get_companies_ownership_changes_business_scope_trading",
        "查詢上市公司經營權及營業範圍異(變)動專區-經營權異動且營業範圍重大變更列為變更交易公司。",
        "經營權異動且營業範圍重大變更列為變更交易公司資料", "經營權異動且營業範圍重大變更列為變更交易公司",
        None, None,
        lambda i: f"- {i.get('公司名稱', 'N/A')} ({i.get('公司代號', 'N/A')}): {i.get('變更日期', 'N/A')}\n",
    ),
    (
        "/opendata/t187ap33_L", "get_company_ceo_dual_role",
        "查詢上市公司董事長是否兼任總經理。", "上市公司董事長兼任總經理資料", "上市公司董事長兼任總經理",
        "公司名稱", "公司名稱關鍵字",
        lambda i: f"- {i.get('公司名稱', 'N/A')} ({i.get('公司代號', 'N/A')}): {i.get('董事長是否兼任總經理', 'N/A')}\n",
    ),
    (
        "/opendata/t187ap34_L", "get_companies_cumulative_voting",
        "查詢上市公司採累積投票制、全額連記法、候選人提名制選任董監事及當選資料彙總表。",
        "上市公司採累積投票制選任董監事資料", "上市公司採累積投票制選任董監事",
        "公司名稱", "公司名稱關鍵字", _fmt_cumulative_voting,
    ),
    (
        "/opendata/t187ap35_L", "get_company_shareholder_proposal_exercise",
        "查詢上市公司股東行使提案權情形彙總表。", "上市公司股東行使提案權資料", "上市公司股東行使提案權",
        "公司名稱", "公司名稱關鍵字", _fmt_proposal_exercise,
    ),
]

# Simple tools: (endpoint, function_name, mcp_description)
# All follow the same pattern: fetch_company_data(endpoint, code) → format as properties.
SIMPLE_BASIC_INFO_TOOLS = [
    ("/opendata/t187ap03_L", "get_company_profile",
     "根據股票代號查詢上市公司基本資料。"),
    ("/opendata/t187ap45_L", "get_company_dividend",
     "根據股票代號查詢上市公司股利分派情形。"),
    ("/opendata/t187ap05_L", "get_company_monthly_revenue",
     "根據股票代號查詢上市公司每月營業收入彙總表。"),
    ("/opendata/t187ap05_P", "get_public_company_monthly_revenue",
     "根據股票代號查詢公開發行公司每月營業收入彙總表。"),
    ("/opendata/t187ap02_L", "get_company_major_shareholders",
     "根據股票代號查詢上市公司持股逾10%大股東名單。"),
    ("/opendata/t187ap14_L", "get_company_eps_statistics",
     "根據股票代號查詢上市公司各產業EPS統計資訊。"),
    ("/opendata/t187ap11_L", "get_company_board_shareholdings",
     "根據股票代號查詢上市公司董監事持股餘額明細資料。"),
    ("/opendata/t187ap12_L", "get_company_daily_insider_trades_preannounced",
     "根據股票代號查詢上市公司每日內部人持股轉讓事前申報表-持股轉讓日報表。"),
    ("/opendata/t187ap13_L", "get_company_daily_insider_trades_untransferred",
     "根據股票代號查詢上市公司每日內部人持股轉讓事前申報表-持股未轉讓日報表。"),
    ("/opendata/t187ap22_L", "get_company_sec_regulatory_penalties",
     "根據股票代號查詢上市公司金管會證券期貨局裁罰案件專區。"),
    ("/opendata/t187ap29_A_L", "get_company_director_compensation",
     "根據股票代號查詢上市公司董事酬金相關資訊。"),
    ("/opendata/t187ap29_B_L", "get_company_supervisor_compensation",
     "根據股票代號查詢上市公司監察人酬金相關資訊。"),
    ("/opendata/t187ap29_C_L", "get_company_consolidated_director_compensation",
     "根據股票代號查詢上市公司合併報表董事酬金相關資訊。"),
    ("/opendata/t187ap29_D_L", "get_company_consolidated_supervisor_compensation",
     "根據股票代號查詢上市公司合併報表監察人酬金相關資訊。"),
    ("/opendata/t187ap23_L", "get_company_information_disclosure_violations",
     "根據股票代號查詢上市公司違反資訊申報、重大訊息及說明記者會規定專區。"),
    ("/opendata/t187ap03_P", "get_public_company_profile",
     "根據股票代號查詢公開發行公司基本資料。"),
    ("/opendata/t187ap32_L", "get_company_governance_regulations",
     "根據股票代號查詢上市公司公司治理之相關規程規則。"),
]


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company basic info tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    for endpoint, name, doc in SIMPLE_BASIC_INFO_TOOLS:
        create_company_tool(mcp, endpoint, name, doc, client)

    for endpoint, name, summary, label, empty_type, filter_field, name_label, formatter in SIMPLE_LIST_TOOLS:
        create_list_tool(
            mcp, endpoint, name,
            _list_doc(summary, name_label, has_name=filter_field is not None),
            label, empty_type, formatter, filter_field=filter_field, client=client,
        )

    # --- Complex tools with custom logic ---

    @mcp.tool
    @handle_api_errors()
    def get_company_board_insufficient_shares(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市公司董事、監察人持股不足法定成數彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap08_L")
        if not data:
            return MSG_NO_DATA.format(data_type="董監事持股不足法定成數")

        deficient = [
            item for item in data
            if item.get("全體董事不足股數", "") or item.get("全體監察人不足股數", "")
        ]
        if name:
            deficient = [d for d in deficient if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            parts = []
            if item.get("全體董事不足股數", ""):
                parts.append(f"董事不足 {item['全體董事不足股數']} 股")
            if item.get("全體監察人不足股數", ""):
                parts.append(f"監察人不足 {item['全體監察人不足股數']} 股")
            return f"- {company_name} ({company_code}): {', '.join(parts)}\n"

        return format_list_response(deficient, "董監事持股不足法定成數資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_companies_with_independent_directors(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市公司獨立董監事兼任情形彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap30_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司獨立董監事兼任情形")

        companies: dict = {}
        for item in data:
            code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            if code != "N/A":
                companies[code] = company_name

        sorted_companies = sorted(companies.items())
        if name:
            sorted_companies = [(c, n) for c, n in sorted_companies if name in n]

        total = len(sorted_companies)
        page_data = sorted_companies[offset:offset + limit]
        end = min(offset + limit, total)

        header = f"共有 {total} 家公司具有獨立董監事資料"
        if total > limit or offset > 0:
            header += f"（顯示第 {offset + 1}–{end} 筆）"
        header += "：\n\n"

        result = header + "".join(f"- {company_name} ({code})\n" for code, company_name in page_data)

        remaining = total - offset - limit
        if remaining > 0:
            result += f"\n... 還有 {remaining} 筆，使用 offset={offset + limit} 查看更多"

        return result

    @mcp.tool
    @handle_api_errors()
    def get_companies_with_csr_reports_103(limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢民國103年應編製及申報企業社會責任報告書之公司。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/static/20151104/CSR103")
        if not data:
            return (
                "查無 103 年度 CSR 報告名單或資料格式不符（來源可能為舊式靜態頁）。\n"
                "建議改查近年永續報告（ESG）相關端點，或至公司官網/公告查詢。"
            )

        valid = [it for it in data if isinstance(it, dict) and has_meaningful_data(it, ["公司代號", "公司名稱"])]
        if not valid:
            return "查無有效的公司名單（欄位皆為空或 N/A）。\n請稍後再試或改查其他相關來源。"

        def formatter(item):
            return f"- {item.get('公司名稱', 'N/A')} ({item.get('公司代號', 'N/A')})\n"

        return format_list_response(valid, "103年度需編製CSR報告書公司", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_company_board_insufficient_shares_consecutive() -> str:
        """查詢上市公司董事、監察人持股不足法定成數連續達3個月以上彙總表。"""
        data = _client.fetch_data("/opendata/t187ap10_L")
        if not data:
            return MSG_NO_DATA.format(data_type="")

        result = "董監事持股不足法定成數連續達 3 個月以上的公司：\n\n"
        for item in data:
            for month_field in ["連續不足達3個月", "連續不足達4個月", "連續不足達5個月",
                                "連續不足達6個月", "連續不足達7個月", "連續不足達8個月",
                                "連續不足達9個月", "連續不足達10個月", "連續不足達11個月",
                                "連續不足達12個月", "連續不足逾1年以上"]:
                codes = item.get(month_field, "")
                if codes and codes.strip():
                    result += f"{month_field}: {codes}\n"
        return result

    @mcp.tool
    @handle_api_errors()
    def get_company_shareholder_meeting_announcements(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市公司股東會公告-召集股東常(臨時)會公告資料彙總表(95年度起適用)。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap38_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司股東會公告")

        filtered = [
            it for it in data
            if isinstance(it, dict) and has_meaningful_data(it, [
                "公司代號", "公司名稱", "股東常(臨時)會日期-日期", "股東常(臨時)會日期-常或臨時"
            ])
        ]
        if not filtered:
            return "查無有效的股東會公告資料。"

        if name:
            filtered = [d for d in filtered if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            meaningful_fields = format_meaningful_fields_only(item, ["公司代號", "公司名稱", "出表日期"])
            result = f"【{company_name} ({company_code})】\n"
            if meaningful_fields:
                indented = "\n".join(f"   {line}" for line in meaningful_fields.split("\n") if line.strip())
                result += f"{indented}\n"
            return result + "\n"

        return format_list_response(filtered, "上市公司股東會公告資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_shareholder_meeting_announcements_by_code(code: str) -> str:
        """根據股票代號查詢上市公司股東會公告-召集股東常(臨時)會公告資料彙總表。"""
        data = _client.fetch_company_data("/opendata/t187ap38_L", code)
        if not data:
            return f"查無股票代碼 {code} 的股東會公告資料。"

        if not has_meaningful_data(data, [
            "公司代號", "公司名稱", "股東常(臨時)會日期-日期", "股東常(臨時)會日期-常或臨時"
        ]):
            return f"股票代碼 {code} 的股東會公告資料無效或不完整。"

        company_name = data.get("公司名稱", "N/A")
        company_code = data.get("公司代號", code)
        result = f"{company_name} ({company_code}) 股東會公告資訊：\n\n"
        meaningful_fields = format_meaningful_fields_only(data, ["公司代號", "公司名稱", "出表日期"])
        result += meaningful_fields if meaningful_fields else "無其他詳細資訊。"
        return result

    @mcp.tool
    @handle_api_errors()
    def get_company_shareholder_meeting_dates(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市公司召開股東常(臨時)會日期、地點及採用電子投票情形等資料彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap41_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司股東會日期地點電子投票")

        filtered = [
            it for it in data
            if isinstance(it, dict) and has_meaningful_data(it, [
                "公司代號", "公司名稱", "開會日期", "開會地點", "是否採電子投票"
            ])
        ]
        if not filtered:
            return "查無有效的股東會日期/地點/電子投票資料。"

        if name:
            filtered = [d for d in filtered if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            meeting_date = item.get("開會日期", "N/A")
            location = item.get("開會地點", "N/A")
            electronic_voting = item.get("是否採電子投票", "N/A")
            meeting_type = item.get("股東常(臨時)會", "N/A")
            return f"- {company_name} ({company_code}): {meeting_type} - {meeting_date} at {location}, 電子投票: {electronic_voting}\n"

        return format_list_response(filtered, "上市公司股東會日期地點電子投票資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_companies_with_business_scope_changes(name: str = "", limit: int = DEFAULT_DISPLAY_LIMIT, offset: int = 0) -> str:
        """查詢上市公司經營權及營業範圍異(變)動專區-營業範圍重大變更公司。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap25_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司營業範圍重大變更")

        valid_data = [item for item in data if item.get("公司代號") and item.get("公司名稱")]
        if not valid_data:
            return MSG_NO_DATA.format(data_type="上市公司營業範圍重大變更")

        if name:
            valid_data = [d for d in valid_data if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            year = item.get("年度", "N/A")
            quarter = item.get("季別", "N/A")
            description = item.get("營業範圍重大變更說明", "")
            result = f"- {company_name} ({company_code}): {year}Q{quarter}\n"
            if description:
                result += f"  變更說明: {truncate(description)}\n"
            return result

        return format_list_response(valid_data, "上市公司營業範圍重大變更資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors()
    def get_company_board_pledged_shares() -> str:
        """查詢上市公司董事、監察人質權設定占董事及監察人實際持有股數彙總表。"""
        data = _client.fetch_data("/opendata/t187ap09_L")
        if not data:
            return MSG_NO_DATA.format(data_type="")

        result = "董監事質權設定占實際持有股數資料：\n\n"
        for item in data:
            percentage_range = item.get("百分比", "N/A")
            companies_text = item.get("公司名稱", "")
            if companies_text:
                result += f"質權比例 {percentage_range}%：\n{companies_text}\n\n"
        return result

