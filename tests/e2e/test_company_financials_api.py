"""
測試 company/financials.py 依賴的上游契約：t187ap06/t187ap07 的產業別端點變體互斥。

t187ap06/t187ap07 依產業切成六個端點變體（_ci/_fh/_basi/_bd/_ins/_mim），
工具逐一探測、取第一個含該公司的變體。探測邏輯本身由
tests/test_company_financials_unit.py 離線驗證；這裡只確認「變體互斥」這個前提仍成立。
各變體的 公司代號 欄位則由 tests/tool_field_dependencies.py 驗證。
"""

import pytest
from utils.api_client import TWSEAPIClient
import tools.company.financials as financials


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
    if not seen:
        pytest.skip("t187ap06_L 各變體目前都沒有資料，無法驗證互斥（上游無資料，非 interface 變更）")
