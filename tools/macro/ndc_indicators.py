"""國發會景氣指標／景氣對策信號 and 採購經理人指數 (PMI/NMI).

index.ndc.gov.tw sits behind a Cloudflare bot block, so these read the files NDC itself
publishes on data.gov.tw instead (dataset 6099 景氣指標及燈號, dataset 6100 PMI). The
download links are fixed ws.ndc.gov.tw URLs taken from those dataset pages;
tests/e2e/test_macro_api.py fails if NDC ever re-points them.
"""

import csv
import io
import zipfile
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

# data.gov.tw/dataset/6099 景氣指標及燈號 (zip of CSVs, monthly since 1982)
NDC_BUSINESS_CYCLE_ZIP_URL = (
    "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82Mzky"
    "L2VhMjM1YmQ5LWQwNTItNGE2OS1hYmZjLWQ1Yzc4NWQzZDBlMi56aXA%3d&n=5pmv5rCj5oyH5qiZ5Y%2bK54eI6JmfLnppcA%3d%3d&icon=.zip"
)
# data.gov.tw/dataset/6100 臺灣採購經理人指數 (CSV: Date,PMI,NMI)
NDC_PMI_CSV_URL = (
    "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82Mzkx"
    "L2JmOGE0ZWI3LTEwZmUtNGZhMC1iNjQ2LTMwZTg5MGQwMjE4YS5jc3Y%3d&n=6Ie654Gj5o6h6LO857aT55CG5Lq65oyH5pW4KHBtaeWPim5taSkuY3N2&icon=.csv"
)

# CSV files inside the 6099 zip, by the name the tool exposes.
CYCLE_TABLES = {
    "signal": "景氣指標與燈號.csv",
    "signal_components": "景氣對策信號構成項目.csv",
    "leading": "領先指標構成項目.csv",
    "coincident": "同時指標構成項目.csv",
    "lagging": "落後指標構成項目.csv",
}
MAX_MONTHS = 60


def read_zip_csv(body: bytes, filename: str) -> list:
    """Return the rows (header first) of ``filename`` inside the NDC zip."""
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        for info in zf.infolist():
            if info.filename.rsplit("/", 1)[-1] == filename:
                text = zf.read(info).decode("utf-8-sig")
                return list(csv.reader(io.StringIO(text)))
    raise ValueError(f"國發會景氣指標壓縮檔內找不到 {filename}")


def format_monthly_table(rows: list, months: int, title: str) -> str:
    """Render the last ``months`` rows of a Date-first CSV, one line per month."""
    header, data = rows[0], [r for r in rows[1:] if r and r[0].strip()]
    shown = data[-months:]
    lines = [f"【{title}】（最近 {len(shown)} 個月，空白表示尚未公布）"]
    for r in reversed(shown):
        ym = r[0].strip()
        label = f"{ym[:4]}-{ym[4:]}" if len(ym) == 6 else ym
        cells = [f"{h.strip()}:{v.strip() or '-'}" for h, v in zip(header[1:], r[1:])]
        lines.append(f"{label} | " + " | ".join(cells))
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register NDC business-cycle and PMI tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def get_business_cycle_indicators(months: int = 12, table: str = "signal") -> str:
        """查詢國發會景氣對策信號（景氣燈號）與景氣指標，每月更新，資料自 1982 年起。
        燈號：紅燈(38-45分，熱絡)、黃紅燈(32-37)、綠燈(23-31，穩定)、黃藍燈(17-22)、藍燈(9-16，低迷)。

        Args:
            months: 回傳最近幾個月（預設 12，最多 60）
            table: 資料表，預設 "signal"：
                signal＝景氣對策信號分數與燈號、領先/同時/落後指標綜合指數；
                signal_components＝燈號九項構成項目（M1B、股價指數、工業生產、出口…）；
                leading／coincident／lagging＝領先／同時／落後指標構成項目

        Returns:
            每月（由新到舊）的各欄位數值；最新月份部分項目可能尚未公布
        """
        filename = CYCLE_TABLES.get(table.strip().lower())
        if filename is None:
            return f"table 只能是 {', '.join(CYCLE_TABLES)}"
        months = max(1, min(months, MAX_MONTHS))
        body = _client.fetch_bytes(NDC_BUSINESS_CYCLE_ZIP_URL, timeout=60)
        rows = read_zip_csv(body, filename)
        if len(rows) < 2:
            return "目前沒有國發會景氣指標資料。"
        return format_monthly_table(rows, months, f"國發會 {filename.removesuffix('.csv')}")

    @mcp.tool
    @handle_api_errors()
    def get_taiwan_pmi(months: int = 12) -> str:
        """查詢國發會臺灣採購經理人指數：製造業 PMI 與非製造業 NMI，每月更新（2012 年起）。
        指數 50 以上代表擴張、50 以下代表緊縮，是景氣的領先參考指標。

        Args:
            months: 回傳最近幾個月（預設 12，最多 60）

        Returns:
            每月（由新到舊）的 PMI 與 NMI
        """
        months = max(1, min(months, MAX_MONTHS))
        body = _client.fetch_bytes(NDC_PMI_CSV_URL, timeout=60)
        rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
        if len(rows) < 2:
            return "目前沒有臺灣採購經理人指數資料。"
        return format_monthly_table(rows, months, "臺灣採購經理人指數（PMI 製造業／NMI 非製造業）")
