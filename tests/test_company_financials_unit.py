"""company/financials.py 的產業別報表選擇邏輯（不打網路）。

t187ap06/t187ap07 依產業切成六個端點變體（_ci/_fh/_basi/_bd/_ins/_mim），
每家公司只會出現在其中一個。工具改為逐一探測而非讀 t187ap03_L 的「產業別」
欄位——該欄位是數字代碼（'17' 同時涵蓋金控、銀行、證券、保險），無法據以四分。

上游「六個變體互斥」屬於 interface 契約，由 tests/e2e/test_company_financials_api.py 驗證。
"""

import pytest

from tests.helpers import register_module_tools
from tests.offline import OfflineClient
import tools.company.financials as financials

pytestmark = pytest.mark.offline

# 每個產業變體放一家公司；非 _ci 的公司都曾因舊的中文對照表而回傳空字串
CODE_BY_SUFFIX = {
    "_ci": "2330",
    "_fh": "2884",
    "_basi": "2801",
    "_bd": "2855",
    "_ins": "2850",
    "_mim": "6666",
}


def _routes(prefix):
    return {
        f"{prefix}{suffix}": [{"公司代號": code, "報表": f"{prefix}{suffix}"}]
        for suffix, code in CODE_BY_SUFFIX.items()
    }


@pytest.fixture
def financial_tools():
    client = OfflineClient({**_routes("/opendata/t187ap06_L"), **_routes("/opendata/t187ap07_L")})
    return register_module_tools(financials, client)


@pytest.mark.parametrize("suffix,code", CODE_BY_SUFFIX.items())
def test_income_statement_probes_every_industry_variant(financial_tools, suffix, code):
    """非一般業公司也必須查得到損益表，且要用到它所屬的變體，不能落回 _ci."""
    result = financial_tools["get_company_income_statement"](code)
    assert f"t187ap06_L{suffix}" in result, f"{code} 的綜合損益表未取自 {suffix}: {result!r}"


@pytest.mark.parametrize("suffix,code", CODE_BY_SUFFIX.items())
def test_balance_sheet_probes_every_industry_variant(financial_tools, suffix, code):
    result = financial_tools["get_company_balance_sheet"](code)
    assert f"t187ap07_L{suffix}" in result, f"{code} 的資產負債表未取自 {suffix}: {result!r}"


def test_unknown_code_returns_explicit_message(financial_tools):
    """查無此公司時要回明確訊息，不能是無聲的空字串."""
    result = financial_tools["get_company_income_statement"]("0000")
    assert result.startswith("查無"), f"預期「查無」訊息，實際: {result!r}"
