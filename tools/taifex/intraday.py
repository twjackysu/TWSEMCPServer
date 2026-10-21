"""Futures intraday bars from TAIFEX tick data (每筆成交), any of the last 30 trading days.

Source: www.taifex.com.tw/cht/3/dlFutPrevious30DaysSalesData lists one zip per trading day
(DailydownloadCSV/Daily_YYYY_MM_DD.zip, ~2.5 MB, a ~45 MB cp950 CSV of every futures trade).
The trading day's file starts with its night session (盤後, from 15:00 the evening before,
dated that evening, running past midnight) followed by the day session (一般, 08:45–13:45).
The openapi TimeAndSalesData endpoint has the same rows for the latest day only, as one
~220 MB JSON body, so it is not used.

成交數量(B+S) counts both sides of each trade, so contracts = sum / 2. Measured 2026-10-16
against the daily market report: the night session matches within 0.3%; the day session is
~12% lower because legs filled from calendar-spread orders are not in the tick file.
"""

import re
import threading
import zipfile
import io
from collections import OrderedDict
from typing import Dict, List, Literal, Optional, Tuple

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from utils import TWSEAPIClient
from toolkit import TradingDate, handle_api_errors
from utils.deadline import time_budget
from utils.taifex import TAIFEX_DOWNLOAD_BASE, TAIFEX_HEADERS, is_stock_code, stock_futures_contracts

TICK_PAGE_URL = f"{TAIFEX_DOWNLOAD_BASE}/dlFutPrevious30DaysSalesData"
TICK_ZIP_BASE = "https://www.taifex.com.tw/file/taifex/Dailydownload/DailydownloadCSV"
_TICK_ZIP_RE = re.compile(r"DailydownloadCSV/Daily_(\d{4})_(\d{2})_(\d{2})\.zip")
EXPECTED_HEADER = ["成交日期", "商品代號", "到期月份(週別)", "成交時間", "成交價格", "成交數量(B+S)", "近月價格", "遠月價格", "開盤集合競價"]
# A trading day's file never changes; the page listing refreshes once per evening.
TICK_ZIP_CACHE_TTL = 6 * 3600
TICK_PAGE_CACHE_TTL = 600
Interval = Literal[1, 5, 15, 30, 60]
Session = Literal["day", "night", "all"]  # SESSIONS
SESSIONS = {"day": "日盤", "night": "夜盤", "all": "夜盤＋日盤"}
DAY_START, DAY_END = 8 * 60 + 45, 13 * 60 + 45  # minutes since midnight
NIGHT_START, NIGHT_END = 15 * 60, 5 * 60
MAX_BARS = 300
MAX_PARSED = 16
# Time for one call's requests (utils/deadline.py): the page plus up to three zips (looking for
# a day that already has its day session). Normally a few seconds; each zip may wait up to 120 s.
INTRADAY_BUDGET = 120

Tick = Tuple[str, str, int, float, int]  # date, contract month, HHMMSS, price, volume (B+S)


def available_days(page_html: str) -> List[str]:
    """YYYYMMDD trading days the download page offers, newest first."""
    return sorted({"".join(m) for m in _TICK_ZIP_RE.findall(page_html)}, reverse=True)


def parse_ticks(csv_text: str, contract: str) -> List[Tick]:
    """Single-month trades of one product (calendar-spread rows, month "a/b", dropped)."""
    lines = csv_text.splitlines()
    header = [c.strip() for c in lines[0].split(",")] if lines else []
    if header[: len(EXPECTED_HEADER)] != EXPECTED_HEADER:
        raise ValueError(f"期交所每筆成交 CSV 欄位已變更: {header}")
    ticks = []
    for line in lines[1:]:
        cells = line.split(",")
        if len(cells) < 6 or cells[1].strip() != contract or "/" in cells[2]:
            continue
        try:
            ticks.append((cells[0].strip(), cells[2].strip(), int(cells[3]), float(cells[4]), int(cells[5])))
        except ValueError:
            continue
    return ticks


def products(csv_text: str) -> List[str]:
    return sorted({line.split(",", 2)[1].strip() for line in csv_text.splitlines()[1:] if line.count(",") >= 2})


def session_of(hhmmss: int) -> str:
    minutes = hhmmss // 10000 * 60 + hhmmss // 100 % 100
    return "day" if DAY_START <= minutes <= DAY_END else "night"


def _contracts(volume: float) -> str:
    return f"{volume / 2:,.0f}"


def build_bars(ticks: List[Tick], interval: int, start_minute: int, end_minute: int) -> List[dict]:
    """Bucket chronologically ordered ticks into OHLCV bars aligned to the session start.

    The closing call auction prints exactly at the session end (13:45:00); it closes the last
    bar instead of opening a one-trade bar of its own.
    """
    bars: "OrderedDict[Tuple[str, int], dict]" = OrderedDict()
    length = (end_minute - start_minute) % (24 * 60)
    for date, _month, hhmmss, price, volume in ticks:
        minutes = hhmmss // 10000 * 60 + hhmmss // 100 % 100
        offset = min((minutes - start_minute) % (24 * 60), length - 1)
        bucket = (start_minute + offset // interval * interval) % (24 * 60)
        # Night bars after midnight belong to the next calendar date.
        key = (date, bucket)
        bar = bars.get(key)
        if bar is None:
            bars[key] = {"date": date, "minute": bucket, "open": price, "high": price, "low": price,
                         "close": price, "volume": volume}
        else:
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["close"] = price
            bar["volume"] += volume
    return list(bars.values())


def summarize(ticks: List[Tick]) -> str:
    first, last = ticks[0], ticks[-1]
    high = max(ticks, key=lambda t: t[3])
    low = min(ticks, key=lambda t: t[3])
    total = sum(t[4] for t in ticks)
    vwap = sum(t[3] * t[4] for t in ticks) / total if total else 0

    def clock(t: Tick) -> str:
        return f"{t[2] // 10000:02d}:{t[2] // 100 % 100:02d}:{t[2] % 100:02d}"

    swing = high[3] - low[3]
    return (
        f"開 {first[3]:g}（{clock(first)}）｜高 {high[3]:g}（{clock(high)}）｜低 {low[3]:g}（{clock(low)}）｜"
        f"收 {last[3]:g}（{clock(last)}）｜振幅 {swing:g} 點（{swing / low[3] * 100:.2f}%）｜"
        f"均價 {vwap:,.1f}｜成交 {_contracts(total)} 口、{len(ticks):,} 筆"
    )


def format_session(label: str, ticks: List[Tick], interval: int, start_minute: int, end_minute: int) -> List[str]:
    bars = build_bars(ticks, interval, start_minute, end_minute)
    lines = [f"▍{label}", summarize(ticks)]
    busiest = sorted(bars, key=lambda b: b["volume"], reverse=True)[:3]
    lines.append("成交最集中: " + "、".join(f"{b['minute'] // 60:02d}:{b['minute'] % 60:02d}（{_contracts(b['volume'])} 口）" for b in busiest))
    shown = bars[:MAX_BARS]
    lines.append(f"\n{interval} 分K（共 {len(bars)} 根{f'，僅列前 {MAX_BARS} 根，請加大 interval' if len(bars) > MAX_BARS else ''}）：")
    prev_close = None
    for b in shown:
        change = f" | {b['close'] - prev_close:+g}" if prev_close is not None else ""
        lines.append(f"{b['minute'] // 60:02d}:{b['minute'] % 60:02d} | 開 {b['open']:g} 高 {b['high']:g} 低 {b['low']:g} "
                     f"收 {b['close']:g} | 量 {_contracts(b['volume'])} 口{change}")
        prev_close = b["close"]
    return lines


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the futures intraday tool."""
    _client = client or TWSEAPIClient.get_instance()
    # Shared by concurrent calls (tools run in worker threads): every read and write of
    # `parsed` happens under the lock.
    parsed: "OrderedDict[Tuple[str, str], List[Tick]]" = OrderedDict()
    parsed_lock = threading.Lock()

    def _csv_text(day: str) -> str:
        url = f"{TICK_ZIP_BASE}/Daily_{day[:4]}_{day[4:6]}_{day[6:]}.zip"
        body = _client.fetch_bytes(url, headers=TAIFEX_HEADERS, timeout=120, cache_ttl=TICK_ZIP_CACHE_TTL)
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            return zf.read(zf.namelist()[0]).decode("cp950", errors="replace")

    def _ticks(day: str, contract: str) -> List[Tick]:
        key = (day, contract)
        with parsed_lock:
            ticks = parsed.get(key)
        if ticks is not None:
            return ticks
        # Parse outside the lock (seconds for a ~45 MB file) so cache hits for other days don't
        # wait. Two calls missing the same key both parse; the zip itself is fetched once.
        ticks = parse_ticks(_csv_text(day), contract)
        with parsed_lock:
            parsed.pop(key, None)
            while len(parsed) >= MAX_PARSED:
                parsed.popitem(last=False)
            parsed[key] = ticks
        # Return our own result: another call may evict `key` before we could read it back.
        return ticks

    @mcp.tool
    @handle_api_errors()
    @time_budget(INTRADAY_BUDGET, "已下載的交易日會快取，稍後再試會較快")
    def get_futures_intraday(contract: str = "TX", date: TradingDate = "", interval: Interval = 5, session: Session = "day",
                             month: str = "") -> str:
        """查詢期貨「盤中走勢」：由期交所每筆成交資料彙總成分鐘 K 線，看一整天的多空拉鋸，
        而不只是收盤價。可查最近 30 個交易日（日盤 08:45–13:45、夜盤 15:00–次日 05:00）。
        列出當日開高低收與高低點出現時間、振幅、均價、成交最集中的時段，以及每根 K 線。

        回傳：各時段的開高低收（含時間）、振幅、均價、成交口數與筆數、成交最集中的 3 個時段，以及每根 K 線

        Args:
            contract: 期貨商品代號，預設 TX（臺股期貨）；也可填 MTX、TMF、TE、TF，
                或股票／ETF 代號（例如 "2330"），會自動換成對應的股票期貨。留空則列出當日所有商品代號
            date: 交易日 西元 YYYYMMDD（選填，留空＝最近一個交易日）；夜盤屬於隔天的交易日
            interval: K 線分鐘數，1、5（預設）、15、30、60
            session: day（日盤，預設）、night（夜盤）、all（夜盤＋日盤）
            month: 到期月份，例如 "202611"、"202610W4"（選填，留空＝當日成交量最大的月份，通常是近月）
        """
        page = _client.fetch_bytes(TICK_PAGE_URL, headers=TAIFEX_HEADERS, timeout=60, cache_ttl=TICK_PAGE_CACHE_TTL)
        days = available_days(page.decode("utf-8", errors="replace"))
        if not days:
            raise ValueError("期交所每筆成交下載頁找不到任何檔案連結，頁面可能改版")
        day = date.strip()
        if day and day not in days:
            raise ToolError(f"只能查最近 30 個交易日：{days[-1]}～{days[0]}（{day} 不在範圍內或非交易日）")

        contract = contract.strip().upper()
        if not day:
            # 最新的檔案在日盤開始前只有前一晚的夜盤；以臺股期貨判斷哪一天已有日盤
            day = next((d for d in days[:3] if session == "night"
                        or any(session_of(t[2]) == "day" for t in _ticks(d, "TX"))), days[0])
        if not contract:
            codes = products(_csv_text(day))
            return f"{day} 有成交的期貨商品代號（共 {len(codes)} 種）：\n" + "、".join(codes)

        note = ""
        if is_stock_code(contract):
            matches = stock_futures_contracts(_client, contract)
            if not matches:
                return f"{contract} 沒有股票期貨"
            # 標準型與小型契約同一標的、同一價格：取當日成交筆數多的那一個
            options = [(len(_ticks(day, c)), c) for c, _name in matches]
            _count, chosen = max(options)
            others = [c for c, _n in matches if c != chosen]
            note = f"（{contract} {matches[0][1]} 的股票期貨{'；另有 ' + '、'.join(others) if others else ''}）"
            contract = chosen

        ticks = _ticks(day, contract)
        if not ticks:
            return f"{day} 查無 {contract} 的成交資料（留空 contract 可列出當日商品代號）"
        month = month.strip().upper()
        if not month:
            volume: Dict[str, int] = {}
            for t in ticks:
                volume[t[1]] = volume.get(t[1], 0) + t[4]
            month = max(volume, key=volume.get)
        ticks = [t for t in ticks if t[1] == month]
        if not ticks:
            return f"{day} 查無 {contract} {month} 的成交資料"

        lines = [f"【{contract} {month} 盤中走勢】交易日 {day[:4]}-{day[4:6]}-{day[6:]}｜{SESSIONS[session]}｜{interval} 分K{note}",
                 "（成交口數＝買賣雙邊合計÷2；不含價差單拆出的單腿成交，日盤會比每日行情的成交量少約一成）\n"]
        wanted = ("night", "day") if session == "all" else (session,)
        for name in wanted:
            part = [t for t in ticks if session_of(t[2]) == name]
            if not part:
                lines.append(f"▍{SESSIONS[name]}：無成交\n")
                continue
            start, end = (DAY_START, DAY_END) if name == "day" else (NIGHT_START, NIGHT_END)
            lines += format_session(SESSIONS[name], part, interval, start, end) + [""]
        return "\n".join(lines).rstrip()
