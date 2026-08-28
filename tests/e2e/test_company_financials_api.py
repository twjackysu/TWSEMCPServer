"""
測試 company/financials.py 的產業別報表選擇邏輯。

t187ap06/t187ap07 依產業切成六個端點變體（_ci/_fh/_basi/_bd/_ins/_mim），
每家公司只會出現在其中一個。工具改為逐一探測而非讀 t187ap03_L 的「產業別」
欄位——該欄位是數字代碼（'17' 同時涵蓋金控、銀行、證券、保險），無法據以四分。
"""

import pytest
from tests.helpers import register_module_tools
from utils.api_client import TWSEAPIClient
import tools.company.financials as financials

# 各產業一個代表，全部曾因舊的中文對照表而回傳空字串
FINANCIAL_SECTOR_CODES = ["2884", "2891", "2801", "2855", "2850"]
GENERAL_SECTOR_CODES = ["2330", "1101"]


@pytest.fixture(scope="module")
def financial_tools():
    return register_module_tools(financials, TWSEAPIClient())


@pytest.mark.parametrize("code", FINANCIAL_SECTOR_CODES + GENERAL_SECTOR_CODES)
def test_income_statement_is_not_empty(financial_tools, code):
    """非一般業公司也必須查得到損益表，不能落回 _ci 而回傳空字串."""
    result = financial_tools["get_company_income_statement"](code)
    assert result, f"{code} 的綜合損益表回傳空字串"
    assert not result.startswith("查無"), f"{code} 的綜合損益表查無資料: {result}"


@pytest.mark.parametrize("code", FINANCIAL_SECTOR_CODES + GENERAL_SECTOR_CODES)
def test_balance_sheet_is_not_empty(financial_tools, code):
    """資產負債表同上."""
    result = financial_tools["get_company_balance_sheet"](code)
    assert result, f"{code} 的資產負債表回傳空字串"
    assert not result.startswith("查無"), f"{code} 的資產負債表查無資料: {result}"


def test_unknown_code_returns_explicit_message(financial_tools):
    """查無此公司時要回明確訊息，不能是無聲的空字串."""
    result = financial_tools["get_company_income_statement"]("9999")
    assert result.startswith("查無"), f"預期「查無」訊息，實際: {result!r}"


def test_industry_variants_partition_companies():
    """六個端點變體不重疊：若上游改成有交集，逐一探測的前提就不成立."""
    client = TWSEAPIClient()
    seen = {}
    for suffix in financials.INDUSTRY_SUFFIXES:
        data = client.fetch_data(f"/opendata/t187ap06_L{suffix}")
        for item in data:
            code = item.get("公司代號")
            if not code:
                continue
            assert code not in seen, (
                f"{code} 同時出現在 t187ap06_L{seen[code]} 與 t187ap06_L{suffix}，"
                "端點不再互斥，探測順序會影響結果"
            )
            seen[code] = suffix
    assert len(seen) > 900, f"上市公司總數異常偏低: {len(seen)}"
