"""國發會景氣指標／景氣對策信號 and 採購經理人指數 (PMI/NMI).

The files come from data.gov.tw (index.ndc.gov.tw blocks bots) and are read through
``sources.ndc.indicators``.
"""

from typing import Annotated, Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient
from pydantic import Field
from sources.ndc.indicators import CYCLE_TABLES, MonthlyTable, Table, business_cycle, pmi
from toolkit import handle_api_errors

MAX_MONTHS = 60


def format_monthly_table(table: MonthlyTable, months: int, title: str) -> str:
    """Render the last ``months`` months, newest first, one line per month."""
    shown = table.rows[-months:]
    lines = [f"【{title}】（最近 {len(shown)} 個月，空白表示尚未公布）"]
    for r in reversed(shown):
        cells = [f"{h}:{v or '-'}" for h, v in zip(table.columns, r.values, strict=True)]
        lines.append(f"{r.year:04d}-{r.month:02d} | " + " | ".join(cells))
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register NDC business-cycle and PMI tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_business_cycle_indicators(months: Annotated[int, Field(ge=1, le=MAX_MONTHS)] = 12, table: Table = "signal") -> str:
        """查詢國發會景氣對策信號（景氣燈號）與景氣指標（領先指標、同時指標、落後指標），每月更新，資料自 1982 年起。
        燈號：紅燈(38-45分，熱絡)、黃紅燈(32-37)、綠燈(23-31，穩定)、黃藍燈(17-22)、藍燈(9-16，低迷)。

        回傳：每月（由新到舊）的各欄位數值；最新月份部分項目可能尚未公布

        Args:
            months: 回傳最近幾個月（預設 12，最多 60）
            table: 資料表，預設 "signal"：
                signal＝景氣對策信號分數與燈號、領先/同時/落後指標綜合指數；
                signal_components＝燈號九項構成項目（M1B、股價指數、工業生產、出口…）；
                leading／coincident／lagging＝領先／同時／落後指標構成項目
        """
        data = business_cycle(_client, table)
        if data is None:
            return "目前沒有國發會景氣指標資料。"
        return format_monthly_table(data, months, f"國發會 {CYCLE_TABLES[table].removesuffix('.csv')}")

    @mcp.tool
    @handle_api_errors()
    def get_taiwan_pmi(months: Annotated[int, Field(ge=1, le=MAX_MONTHS)] = 12) -> str:
        """查詢國發會臺灣採購經理人指數：製造業 PMI 與非製造業 NMI，每月更新（2012 年起）。
        指數 50 以上代表擴張、50 以下代表緊縮，是景氣的領先參考指標。

        回傳：每月（由新到舊）的 PMI 與 NMI

        Args:
            months: 回傳最近幾個月（預設 12，最多 60）
        """
        data = pmi(_client)
        if data is None:
            return "目前沒有臺灣採購經理人指數資料。"
        return format_monthly_table(data, months, "臺灣採購經理人指數（PMI 製造業／NMI 非製造業）")
