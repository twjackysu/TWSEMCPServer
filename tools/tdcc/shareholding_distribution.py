"""集保戶股權分散表 (shareholding distribution by holding size) from TDCC open data.

opendata.tdcc.com.tw's dataset 1-5 is one CSV (~2.3 MB) covering every security for the
latest weekly snapshot, so the tool downloads it and filters locally. Only the latest week
is available from this source.
"""

import csv
import io
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TDCC_DISTRIBUTION_URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
# Weekly data in one ~2.3 MB file: without a cache every single-stock lookup re-downloads
# the whole market.
TDCC_CACHE_TTL = 3600

# 持股分級 1–17. Levels 1–15 are holding-size brackets in shares (1 張 = 1,000 股),
# 16 is TDCC's 差異數調整 (reconciliation with the share register), 17 is the total.
LEVELS = {
    "1": "1-999股",
    "2": "1-5張",
    "3": "5-10張",
    "4": "10-15張",
    "5": "15-20張",
    "6": "20-30張",
    "7": "30-40張",
    "8": "40-50張",
    "9": "50-100張",
    "10": "100-200張",
    "11": "200-400張",
    "12": "400-600張",
    "13": "600-800張",
    "14": "800-1000張",
    "15": "1000張以上",
    "16": "差異數調整",
    "17": "合計",
}
BIG_HOLDER_400_LEVELS = ("12", "13", "14", "15")
SMALL_HOLDER_LEVELS = ("1", "2", "3")  # 10 張以下

EXPECTED_HEADER = ["資料日期", "證券代號", "持股分級", "人數", "股數", "占集保庫存數比例%"]


def parse_distribution_csv(body: bytes) -> list:
    """Decode the TDCC CSV (UTF-8 with BOM) into data rows, header excluded."""
    text = body.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or [c.strip() for c in rows[0]] != EXPECTED_HEADER:
        raise ValueError(f"集保股權分散表 CSV 欄位與預期不符: {rows[0] if rows else '空檔案'}")
    return rows[1:]


def summarize(rows: list) -> str:
    """Render one security's 17 level rows plus big/small-holder ratios."""
    by_level = {r[2].strip(): r for r in rows}

    def pct(levels):
        return sum(float(by_level[lv][5]) for lv in levels if lv in by_level)

    def people(levels):
        return sum(int(by_level[lv][3]) for lv in levels if lv in by_level)

    lines = []
    for lv, label in LEVELS.items():
        r = by_level.get(lv)
        if r:
            lines.append(f"{label}: 人數 {int(r[3]):,} | 股數 {int(r[4]):,} | 占比 {r[5]}%")
    lines.append("")
    lines.append(
        f"千張大戶（1000張以上）: {pct(('15',)):.2f}%（{people(('15',)):,} 人）| "
        f"400張以上大戶: {pct(BIG_HOLDER_400_LEVELS):.2f}%（{people(BIG_HOLDER_400_LEVELS):,} 人）| "
        f"10張以下散戶: {pct(SMALL_HOLDER_LEVELS):.2f}%（{people(SMALL_HOLDER_LEVELS):,} 人）"
    )
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TDCC shareholding distribution tools."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_shareholding_distribution(code: str) -> str:
        """查詢個股「集保戶股權分散表」（最新一週）：各持股級距的人數、股數、持股比例，
        並彙總千張大戶、400張以上大戶、10張以下散戶的持股比例，用於觀察籌碼集中度。
        資料來自臺灣集中保管結算所開放資料，每週更新（通常週五/週六公布前一個交易週的資料），
        上市、上櫃、興櫃、ETF 皆可查。

        Args:
            code: 證券代號，例如 "2330"、"0050"

        Returns:
            資料日期、17 個持股分級（1-999股 … 1000張以上、差異數調整、合計）的人數/股數/占比，
            以及大戶/散戶持股比例摘要
        """
        body = _client.fetch_bytes(TDCC_DISTRIBUTION_URL, timeout=60, cache_ttl=TDCC_CACHE_TTL)
        rows = [r for r in parse_distribution_csv(body) if len(r) >= 6 and r[1].strip() == code.strip()]
        if not rows:
            return f"查無證券代號 {code} 的集保股權分散資料"
        data_date = rows[0][0].strip()
        header = f"【{code} 集保戶股權分散表】資料日期: {data_date[:4]}-{data_date[4:6]}-{data_date[6:]}\n"
        return header + summarize(rows)
