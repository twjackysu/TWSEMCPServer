"""集保戶股權分散表 (shareholding distribution by holding size), latest week or a weekly trend.

Two TDCC sources behind one tool:
- opendata.tdcc.com.tw dataset 1-5: one CSV (~2.3 MB) with every security for the latest week.
  One cached request, no session -- used for the latest week.
- The public query page www.tdcc.com.tw/portal/zh/smWeb/qryStock: one security at a time, any of
  the last ~51 weeks. No CAPTCHA, but it is a stateful form flow: GET the page (JSESSIONID cookie
  + a one-time SYNCHRONIZER_TOKEN), then POST once per week; every response carries the token for
  the next POST and a used token is rejected. Used for ``weeks`` > 1.

Compared for 2026-10-02 (2330, 6488, 0050): levels 1-15 and the total are identical. Only the
差異數調整 row differs (the page keeps its sign and omits it when zero; open data uses the
absolute value), so the trend view never uses that row.
"""

import csv
import io
import re
from typing import Dict, List, Optional, Tuple

import requests
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors

TDCC_DISTRIBUTION_URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
# Weekly data in one ~2.3 MB file: without a cache every single-stock lookup re-downloads
# the whole market.
TDCC_CACHE_TTL = 3600

TDCC_QUERY_URL = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"
# A browser-like User-Agent, as for the other website flows.
TDCC_PAGE_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
# Each week costs one POST (plus 0.5 s of client throttling), so keep a call to about a quarter.
MAX_WEEKS = 13
MAX_CACHED_WEEKS = 2048

# 持股分級 1-17. Levels 1-15 are holding-size brackets in shares (1 張 = 1,000 股),
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

_TOKEN_RE = re.compile(r'name="SYNCHRONIZER_TOKEN" value="([^"]+)"')
_FIRST_DATE_RE = re.compile(r'name="firDate" value="(\d+)"')
_DATE_SELECT_RE = re.compile(r'<select name="scaDate".*?</select>', re.S)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


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


def parse_query_page(html: str) -> Tuple[str, str, List[str]]:
    """(one-time token, newest week, selectable weeks newest first) from the query page."""
    token, first = _TOKEN_RE.search(html), _FIRST_DATE_RE.search(html)
    select = _DATE_SELECT_RE.search(html)
    dates = re.findall(r'<option[^>]*value="?(\d{8})', select.group(0)) if select else []
    if not (token and first and dates):
        raise ValueError("集保查詢頁結構與預期不符（找不到 token 或日期清單），頁面可能改版")
    return token.group(1), first.group(1), dates


def parse_result_rows(html: str) -> Dict[str, Tuple[int, int, float]]:
    """Level key -> (people, shares, pct). Levels 1-15 by their number, the total as "total";
    the 差異數調整 row is dropped (see the module docstring)."""
    out: Dict[str, Tuple[int, int, float]] = {}
    for row in _ROW_RE.findall(html):
        cells = [_TAG_RE.sub("", c).strip() for c in _CELL_RE.findall(row)]
        if len(cells) != 5:
            continue
        seq, label, people, shares, pct = cells
        if label.startswith("合"):
            key = "total"
        elif seq.isdigit() and 1 <= int(seq) <= 15:
            key = seq
        else:
            continue
        try:
            out[key] = (int(people.replace(",", "") or 0), int(shares.replace(",", "")), float(pct))
        except ValueError:
            continue
    return out


def week_metrics(levels: Dict[str, Tuple[int, int, float]]) -> Dict[str, float]:
    """Holder counts and ratios of the groups people watch: 千張大戶, 400張以上, 10張以下."""

    def group(keys):
        present = [levels[k] for k in keys if k in levels]
        return sum(p for p, _s, _r in present), sum(r for _p, _s, r in present)

    big_people, big_pct = group(("15",))
    b400_people, b400_pct = group(BIG_HOLDER_400_LEVELS)
    small_people, small_pct = group(SMALL_HOLDER_LEVELS)
    return {
        "total_people": levels["total"][0] if "total" in levels else 0,
        "big_people": big_people, "big_pct": big_pct,
        "b400_people": b400_people, "b400_pct": b400_pct,
        "small_people": small_people, "small_pct": small_pct,
    }


def format_trend(code: str, weekly: List[Tuple[str, Dict[str, float]]]) -> str:
    """Newest-first trend lines with the change against the previous (older) week."""
    lines = [f"【{code} 集保股權分散週趨勢】（共 {len(weekly)} 週，由新到舊；pp＝百分點）\n"]
    for i, (date, m) in enumerate(weekly):
        line = (
            f"{date[:4]}-{date[4:6]}-{date[6:]} | 總人數 {m['total_people']:,} | "
            f"千張大戶 {m['big_pct']:.2f}%（{m['big_people']:,} 人）| "
            f"400張以上 {m['b400_pct']:.2f}%（{m['b400_people']:,} 人）| "
            f"10張以下 {m['small_pct']:.2f}%（{m['small_people']:,} 人）"
        )
        if i + 1 < len(weekly):
            prev = weekly[i + 1][1]
            line += (
                f" | 較前週: 千張大戶 {m['big_pct'] - prev['big_pct']:+.2f}pp（{m['big_people'] - prev['big_people']:+,} 人）、"
                f"400張以上 {m['b400_pct'] - prev['b400_pct']:+.2f}pp、"
                f"10張以下 {m['small_pct'] - prev['small_pct']:+.2f}pp（{m['small_people'] - prev['small_people']:+,} 人）"
            )
        lines.append(line)
    return "\n".join(lines)


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register TDCC shareholding distribution tools."""
    _client = client or TWSEAPIClient.get_instance()
    # Past weeks never change, so keep them for the life of the process (bounded).
    week_cache: Dict[Tuple[str, str], Dict[str, Tuple[int, int, float]]] = {}

    def _latest_week_table(code: str) -> str:
        body = _client.fetch_bytes(TDCC_DISTRIBUTION_URL, timeout=60, cache_ttl=TDCC_CACHE_TTL)
        rows = [r for r in parse_distribution_csv(body) if len(r) >= 6 and r[1].strip() == code]
        if not rows:
            return f"查無證券代號 {code} 的集保股權分散資料"
        data_date = rows[0][0].strip()
        header = f"【{code} 集保戶股權分散表】資料日期: {data_date[:4]}-{data_date[4:6]}-{data_date[6:]}\n"
        return header + summarize(rows)

    def _weekly_trend(code: str, weeks: int) -> str:
        session = requests.Session()

        def get_page():
            html = _client.fetch_bytes(
                TDCC_QUERY_URL, headers=TDCC_PAGE_HEADERS, timeout=60, session=session
            ).decode("utf-8", errors="replace")
            return parse_query_page(html)

        token, first_date, dates = get_page()
        weekly: List[Tuple[str, Dict[str, float]]] = []
        for date in dates[:weeks]:
            levels = week_cache.get((code, date))
            if levels is None:
                body = _client.fetch_bytes(
                    TDCC_QUERY_URL, method="POST", headers=TDCC_PAGE_HEADERS, timeout=60, session=session,
                    data={"SYNCHRONIZER_TOKEN": token, "SYNCHRONIZER_URI": "/portal/zh/smWeb/qryStock",
                          "method": "submit", "firDate": first_date, "scaDate": date,
                          "sqlMethod": "StockNo", "stockNo": code, "stockName": ""},
                ).decode("utf-8", errors="replace")
                nxt = _TOKEN_RE.search(body)
                # Each token works once; if the reply carries none, reload the page for a fresh one.
                token = nxt.group(1) if nxt else get_page()[0]
                levels = parse_result_rows(body)
                if "total" not in levels:
                    if not weekly and "查無此資料" in body:
                        return f"查無證券代號 {code} 的集保股權分散資料"
                    continue  # no data for that week
                if len(week_cache) >= MAX_CACHED_WEEKS:
                    week_cache.pop(next(iter(week_cache)))
                week_cache[(code, date)] = levels
            weekly.append((date, week_metrics(levels)))
        if not weekly:
            return f"查無證券代號 {code} 的集保股權分散資料"
        return format_trend(code, weekly)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_shareholding_distribution(code: str, weeks: int = 1) -> str:
        """查詢個股「集保戶股權分散表」，觀察籌碼集中度：預設最新一週的完整級距表；
        weeks > 1 時改為逐週趨勢（最多 13 週）：每週的總人數、千張大戶／400張以上／10張以下散戶的
        持股比例與人數，以及較前一週的增減，可看出大戶是在增持還是減持。
        資料來自臺灣集中保管結算所，每週更新（通常週五／週六公布前一個交易週的資料），
        上市、上櫃、興櫃、ETF 皆可查。

        Args:
            code: 證券代號，例如 "2330"、"0050"
            weeks: 週數（預設 1＝最新一週的完整 17 級距表；2～13＝逐週趨勢，每多一週多一次查詢，較慢）

        Returns:
            weeks=1：資料日期、17 個持股分級的人數／股數／占比，以及大戶／散戶摘要；
            weeks>1：由新到舊每週的大戶與散戶持股比例、人數與週變化
        """
        code = code.strip()
        if weeks < 1 or weeks > MAX_WEEKS:
            return f"weeks 必須介於 1～{MAX_WEEKS}"
        return _latest_week_table(code) if weeks == 1 else _weekly_trend(code, weeks)
