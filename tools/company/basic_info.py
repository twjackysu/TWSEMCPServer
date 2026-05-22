"""Company basic information tools."""

from typing import Optional
from fastmcp import FastMCP
from utils import (
    TWSEAPIClient,
    format_properties_with_values_multiline,
    has_meaningful_data,
    format_meaningful_fields_only,
    MSG_NO_DATA,
    MSG_QUERY_FAILED,
    handle_api_errors,
    format_list_response,
)

def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register company basic info tools with the MCP instance."""

    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_profile(code: str) -> str:
        """根據股票代號查詢上市公司基本資料。"""
        data = _client.fetch_company_data("/opendata/t187ap03_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_dividend(code: str) -> str:
        """根據股票代號查詢上市公司股利分派情形。"""
        data = _client.fetch_company_data("/opendata/t187ap45_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_monthly_revenue(code: str) -> str:
        """根據股票代號查詢上市公司每月營業收入彙總表。"""
        data = _client.fetch_company_data("/opendata/t187ap05_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_public_company_monthly_revenue(code: str) -> str:
        """根據股票代號查詢公開發行公司每月營業收入彙總表。"""
        data = _client.fetch_company_data("/opendata/t187ap05_P", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_major_shareholders(code: str) -> str:
        """根據股票代號查詢上市公司持股逾10%大股東名單。"""
        data = _client.fetch_company_data("/opendata/t187ap02_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_eps_statistics(code: str) -> str:
        """根據股票代號查詢上市公司各產業EPS統計資訊。"""
        data = _client.fetch_company_data("/opendata/t187ap14_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(data_type="董監事持股不足法定成數")
    def get_company_board_insufficient_shares(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司董事、監察人持股不足法定成數彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap08_L")
        if not data:
            return MSG_NO_DATA.format(data_type="董監事持股不足法定成數")

        deficient = []
        for item in data:
            director_insufficient = item.get("全體董事不足股數", "")
            supervisor_insufficient = item.get("全體監察人不足股數", "")
            if director_insufficient or supervisor_insufficient:
                deficient.append(item)

        if name:
            deficient = [d for d in deficient if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            director_insufficient = item.get("全體董事不足股數", "")
            supervisor_insufficient = item.get("全體監察人不足股數", "")
            parts = []
            if director_insufficient:
                parts.append(f"董事不足 {director_insufficient} 股")
            if supervisor_insufficient:
                parts.append(f"監察人不足 {supervisor_insufficient} 股")
            return f"- {company_name} ({company_code}): {', '.join(parts)}\n"

        return format_list_response(deficient, "董監事持股不足法定成數資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_board_shareholdings(code: str) -> str:
        """根據股票代號查詢上市公司董監事持股餘額明細資料。"""
        data = _client.fetch_company_data("/opendata/t187ap11_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_company_daily_insider_trades_preannounced(code: str) -> str:
        """根據股票代號查詢上市公司每日內部人持股轉讓事前申報表-持股轉讓日報表。"""
        data = _client.fetch_company_data("/opendata/t187ap12_L", code)
        return format_properties_with_values_multiline(data) if data else ""

    @mcp.tool
    def get_company_daily_insider_trades_untransferred(code: str) -> str:
        """根據股票代號查詢上市公司每日內部人持股轉讓事前申報表-持股未轉讓日報表。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap13_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_company_sec_regulatory_penalties(code: str) -> str:
        """根據股票代號查詢上市公司金管會證券期貨局裁罰案件專區。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap22_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="上市公司獨立董監事兼任情形")
    def get_companies_with_independent_directors(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司獨立董監事兼任情形彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap30_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司獨立董監事兼任情形")

        from collections import defaultdict
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

        result = header
        for code, company_name in page_data:
            result += f"- {company_name} ({code})\n"

        remaining = total - offset - limit
        if remaining > 0:
            result += f"\n... 還有 {remaining} 筆，使用 offset={offset + limit} 查看更多"

        return result

    @mcp.tool
    def get_company_director_compensation(code: str) -> str:
        """根據股票代號查詢上市公司董事酬金相關資訊。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap29_A_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_company_supervisor_compensation(code: str) -> str:
        """根據股票代號查詢上市公司監察人酬金相關資訊。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap29_B_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_company_consolidated_director_compensation(code: str) -> str:
        """根據股票代號查詢上市公司合併報表董事酬金相關資訊。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap29_C_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_company_consolidated_supervisor_compensation(code: str) -> str:
        """根據股票代號查詢上市公司合併報表監察人酬金相關資訊。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap29_D_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    def get_company_information_disclosure_violations(code: str) -> str:
        """根據股票代號查詢上市公司違反資訊申報、重大訊息及說明記者會規定專區。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap23_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="103年度CSR報告書公司名單")
    def get_companies_with_csr_reports_103(limit: int = 50, offset: int = 0) -> str:
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

        valid = [
            it for it in data
            if isinstance(it, dict) and has_meaningful_data(it, ["公司代號", "公司名稱"])
        ]
        if not valid:
            return "查無有效的公司名單（欄位皆為空或 N/A）。\n請稍後再試或改查其他相關來源。"

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            return f"- {company_name} ({company_code})\n"

        return format_list_response(valid, "103年度需編製CSR報告書公司", formatter, limit=limit, offset=offset)

    @mcp.tool
    def get_public_company_profile(code: str) -> str:
        """根據股票代號查詢公開發行公司基本資料。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap03_P", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="集中市場公布處置股票")
    def get_market_disposal_stocks(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢集中市場公布處置股票。

        Args:
            name: 股票名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/announcement/punish")
        if not data:
            return MSG_NO_DATA.format(data_type="集中市場公布處置股票")

        if name:
            data = [d for d in data if name in d.get("Name", "")]

        def formatter(item):
            stock_code = item.get("Code", "N/A")
            stock_name = item.get("Name", "N/A")
            disposal_measures = item.get("DispositionMeasures", "N/A")
            reasons = item.get("ReasonsOfDisposition", "N/A")
            return f"- {stock_name} ({stock_code}): {disposal_measures} - {reasons}\n"

        return format_list_response(data, "集中市場公布處置股票", formatter, limit=limit, offset=offset)

    @mcp.tool
    def get_company_board_insufficient_shares_consecutive() -> str:
        """查詢上市公司董事、監察人持股不足法定成數連續達3個月以上彙總表。"""
        try:
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
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="上市公司股東會公告")
    def get_company_shareholder_meeting_announcements(name: str = "", limit: int = 50, offset: int = 0) -> str:
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
    def get_company_shareholder_meeting_announcements_by_code(code: str) -> str:
        """根據股票代號查詢上市公司股東會公告-召集股東常(臨時)會公告資料彙總表。"""
        try:
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
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="上市公司經營權異動")
    def get_companies_with_ownership_changes(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司經營權及營業範圍異(變)動專區-經營權異動公司。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap24_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司經營權異動")

        if name:
            data = [d for d in data if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            change_date = item.get("經營權異動日期", "N/A")
            change_desc = item.get("經營權異動說明", "")
            result = f"- {company_name} ({company_code}): {change_date}\n"
            if change_desc:
                result += f"  說明: {change_desc[:100]}...\n" if len(change_desc) > 100 else f"  說明: {change_desc}\n"
            return result

        return format_list_response(data, "上市公司經營權異動資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="上市公司股東會日期地點電子投票")
    def get_company_shareholder_meeting_dates(name: str = "", limit: int = 50, offset: int = 0) -> str:
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
    @handle_api_errors(data_type="上市公司營業範圍重大變更")
    def get_companies_with_business_scope_changes(name: str = "", limit: int = 50, offset: int = 0) -> str:
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
                result += f"  變更說明: {description[:100]}...\n" if len(description) > 100 else f"  變更說明: {description}\n"
            return result

        return format_list_response(valid_data, "上市公司營業範圍重大變更資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="經營權異動且營業範圍重大變更停止買賣公司")
    def get_companies_ownership_changes_business_scope(limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司經營權及營業範圍異(變)動專區-經營權異動且營業範圍重大變更停止買賣公司。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap26_L")
        if not data:
            return MSG_NO_DATA.format(data_type="經營權異動且營業範圍重大變更停止買賣公司")

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            suspension_date = item.get("停止買賣日期", "N/A")
            return f"- {company_name} ({company_code}): {suspension_date}\n"

        return format_list_response(data, "經營權異動且營業範圍重大變更停止買賣公司資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="經營權異動且營業範圍重大變更列為變更交易公司")
    def get_companies_ownership_changes_business_scope_trading(limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司經營權及營業範圍異(變)動專區-經營權異動且營業範圍重大變更列為變更交易公司。

        Args:
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap27_L")
        if not data:
            return MSG_NO_DATA.format(data_type="經營權異動且營業範圍重大變更列為變更交易公司")

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            change_date = item.get("變更日期", "N/A")
            return f"- {company_name} ({company_code}): {change_date}\n"

        return format_list_response(data, "經營權異動且營業範圍重大變更列為變更交易公司資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    def get_company_governance_regulations(code: str) -> str:
        """根據股票代號查詢上市公司公司治理之相關規程規則。"""
        try:
            data = _client.fetch_company_data("/opendata/t187ap32_L", code)
            return format_properties_with_values_multiline(data) if data else ""
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="上市公司董事長兼任總經理")
    def get_company_ceo_dual_role(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司董事長是否兼任總經理。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap33_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司董事長兼任總經理")

        if name:
            data = [d for d in data if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            dual_role = item.get("董事長是否兼任總經理", "N/A")
            return f"- {company_name} ({company_code}): {dual_role}\n"

        return format_list_response(data, "上市公司董事長兼任總經理資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    def get_company_board_pledged_shares() -> str:
        """查詢上市公司董事、監察人質權設定占董事及監察人實際持有股數彙總表。"""
        try:
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
        except Exception as e:
            return MSG_QUERY_FAILED.format(error=str(e))

    @mcp.tool
    @handle_api_errors(data_type="上市公司採累積投票制選任董監事")
    def get_companies_cumulative_voting(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司採累積投票制、全額連記法、候選人提名制選任董監事及當選資料彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap34_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司採累積投票制選任董監事")

        if name:
            data = [d for d in data if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            voting_system = item.get("董監事選任方式", "N/A")
            meeting_date = item.get("股東常(臨時)會日期-日期", "")
            result = f"- {company_name} ({company_code}): {voting_system}"
            if meeting_date:
                result += f" (股東會日期: {meeting_date})"
            return result + "\n"

        return format_list_response(data, "上市公司採累積投票制選任董監事資料", formatter, limit=limit, offset=offset)

    @mcp.tool
    @handle_api_errors(data_type="上市公司股東行使提案權")
    def get_company_shareholder_proposal_exercise(name: str = "", limit: int = 50, offset: int = 0) -> str:
        """查詢上市公司股東行使提案權情形彙總表。

        Args:
            name: 公司名稱關鍵字（選填）
            limit: 回傳筆數上限（預設 50）
            offset: 跳過前 N 筆（預設 0，搭配 limit 分頁）
        """
        data = _client.fetch_data("/opendata/t187ap35_L")
        if not data:
            return MSG_NO_DATA.format(data_type="上市公司股東行使提案權")

        if name:
            data = [d for d in data if name in d.get("公司名稱", "")]

        def formatter(item):
            company_code = item.get("公司代號", "N/A")
            company_name = item.get("公司名稱", "N/A")
            meeting_date = item.get("召開股東會日期", "N/A")
            proposal_period = item.get("股東依公司法第172條之1行使提案權-提案受理期間", "")
            proposal_content = item.get("提案內容", "")
            result = f"- {company_name} ({company_code}): 股東會 {meeting_date}\n"
            if proposal_period:
                result += f"  提案受理期間: {proposal_period}\n"
            if proposal_content:
                result += f"  提案內容: {proposal_content[:100]}...\n" if len(proposal_content) > 100 else f"  提案內容: {proposal_content}\n"
            return result

        return format_list_response(data, "上市公司股東行使提案權資料", formatter, limit=limit, offset=offset)
