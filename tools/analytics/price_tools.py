"""還原權息股價 and 技術指標 for one listed or OTC stock, computed from the exchanges' daily
prices and ex-rights results (see services/price_series.py).

Both reply with text and with the same data as structured content (``AdjustedPriceHistory``,
``TechnicalIndicators``; see toolkit/structured.py). Their size is bounded by the 12-month span and
the 60-day list."""

from dataclasses import dataclass
from datetime import date
from typing import Annotated, List, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import Field

from utils import TWSEAPIClient
from toolkit import handle_api_errors, output_schema, structured_reply
from utils.date_helper import taipei_today
from utils.indicators import bollinger, kd, macd, rsi, sma
from services.price_series import adjust_bars, fetch_daily_bars, fetch_exright_events, months_back

MAX_MONTHS = 12
# 60-day MA and MACD(26+9) need ~90 trading days of history before the first shown value.
INDICATOR_MONTHS = 7
MA_PERIODS = (5, 10, 20, 60)

Code = Annotated[str, Field(description="股票代號")]
Name = Annotated[str, Field(description="公司簡稱")]
MarketName = Annotated[str, Field(description="上市 或 上櫃")]
Day = Annotated[date, Field(description="交易日（西元）")]


@dataclass(frozen=True)
class AdjustedBar:
    """一個交易日；價格已依該日之後到今天的每次除權息往前還原。"""

    day: Day
    open: Annotated[Optional[float], Field(description="還原開盤價（元）")]
    high: Annotated[Optional[float], Field(description="還原最高價（元）")]
    low: Annotated[Optional[float], Field(description="還原最低價（元）")]
    close: Annotated[Optional[float], Field(description="還原收盤價（元）")]
    raw_close: Annotated[Optional[float], Field(description="原始（未還原）收盤價（元）")]
    volume: Annotated[float, Field(description="成交量（股）")]


@dataclass(frozen=True)
class Adjustment:
    """一次除權息事件，以及套用到之前每個價格的還原因子。"""

    day: Annotated[date, Field(description="除權息交易日（西元）")]
    kind: Annotated[str, Field(description="除權、除息 或 權息")]
    close_before: Annotated[float, Field(description="除權息前收盤價（元）")]
    reference: Annotated[float, Field(description="除權息參考價（元）")]
    factor: Annotated[float, Field(description="還原因子＝參考價÷除權息前收盤價；之前的每個價格乘上它")]


@dataclass(frozen=True)
class AdjustedPriceHistory:
    """一檔股票的還原權息日K。"""

    code: Code
    name: Name
    market: MarketName
    adjustments: Annotated[List[Adjustment], Field(description="查詢期間第一天至今的除權息事件，由舊到新；空＝還原價等於原始價")]
    bars: Annotated[List[AdjustedBar], Field(description="每個交易日，由舊到新")]


@dataclass(frozen=True)
class IndicatorDay:
    """一個交易日的技術指標（歷史資料不足以計算的為 null）。"""

    day: Day
    close: Annotated[float, Field(description="收盤價（元；adjusted 為 true 時是還原權息價）")]
    ma5: Annotated[Optional[float], Field(description="5 日均線")]
    ma10: Annotated[Optional[float], Field(description="10 日均線")]
    ma20: Annotated[Optional[float], Field(description="20 日均線")]
    ma60: Annotated[Optional[float], Field(description="60 日均線")]
    k: Annotated[Optional[float], Field(description="KD(9,3,3) 的 K")]
    d: Annotated[Optional[float], Field(description="KD(9,3,3) 的 D")]
    rsi14: Annotated[Optional[float], Field(description="RSI(14)")]
    dif: Annotated[Optional[float], Field(description="MACD(12,26,9) 的 DIF")]
    macd: Annotated[Optional[float], Field(description="MACD(12,26,9) 的訊號線（DIF 的 9 日 EMA）")]
    osc: Annotated[Optional[float], Field(description="MACD 柱狀體＝DIF－MACD")]
    bollinger_upper: Annotated[Optional[float], Field(description="布林通道(20,2) 上軌")]
    bollinger_middle: Annotated[Optional[float], Field(description="布林通道(20,2) 中軌（20 日均線）")]
    bollinger_lower: Annotated[Optional[float], Field(description="布林通道(20,2) 下軌")]
    volume: Annotated[float, Field(description="成交量（股）")]
    volume_ma5: Annotated[Optional[float], Field(description="5 日均量（股）")]
    volume_ma20: Annotated[Optional[float], Field(description="20 日均量（股）")]


@dataclass(frozen=True)
class TechnicalIndicators:
    """一檔股票最近交易日的技術指標。"""

    code: Code
    name: Name
    market: MarketName
    adjusted: Annotated[bool, Field(description="是否以還原權息價計算")]
    sample_start: Annotated[date, Field(description="計算所用樣本的第一個交易日（西元）")]
    sample_days: Annotated[int, Field(description="計算所用樣本的交易日數")]
    days: Annotated[List[IndicatorDay], Field(description="最近的交易日，由舊到新；最後一筆是最新一日")]


def _fmt(v: Optional[float], digits: int = 2) -> str:
    return "-" if v is None else f"{v:,.{digits}f}"


def parse_months(start_month: str, end_month: str) -> tuple:
    """(start (y, m), month count) for YYYYMM inputs, defaulting to the last 3 months."""
    if not start_month:
        return None, 3
    try:
        sy, sm = int(start_month[:4]), int(start_month[4:6])
        end = end_month or start_month
        ey, em = int(end[:4]), int(end[4:6])
        date(sy, sm, 1), date(ey, em, 1)
        if len(start_month) != 6 or len(end) != 6:
            raise ValueError
    except ValueError:
        return "月份格式錯誤，請使用 YYYYMM，例如 \"202601\"", 0
    count = (ey - sy) * 12 + (em - sm) + 1
    if count < 1:
        return "起始月份不可晚於結束月份", 0
    if count > MAX_MONTHS:
        return f"查詢區間最多 {MAX_MONTHS} 個月", 0
    return (ey, em), count


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool(output_schema=output_schema(AdjustedPriceHistory))
    @handle_api_errors(use_code_param=True)
    def get_adjusted_price_history(code: str, start_month: str = "", end_month: str = "") -> ToolResult:
        """查詢上市或上櫃股票的「還原權息」日K：把除權息造成的價格缺口還原，才能正確比較長期漲跌與報酬。
        以證交所／櫃買中心公告的除權息參考價計算還原因子（參考價÷除權息前收盤價），往前回溯調整。

        回傳：每個交易日的還原開高低收、原始收盤價、成交量（股），以及期間內套用的除權息事件與還原因子

        Args:
            code: 股票代號，例如 "2330"、"6488"（自動判斷上市或上櫃）
            start_month: 起始月份 西元 YYYYMM（選填，預設最近 3 個月）
            end_month: 結束月份 西元 YYYYMM（選填，預設同 start_month）。區間最多 12 個月
        """
        end, count = parse_months(start_month.strip(), end_month.strip())
        if isinstance(end, str):
            raise ToolError(end)
        months = months_back(count, date(*end, 1) if end else None)
        market, name, bars = fetch_daily_bars(_client, code.strip(), months)
        if not bars:
            raise ToolError(f"查無 {code} 在 {months[0][0]}-{months[0][1]:02d}～{months[-1][0]}-{months[-1][1]:02d} "
                            f"的上市／上櫃交易資料")

        # 還原要考慮查詢區間之後到今天的除權息，否則較早的價格會少乘後面的因子
        events = fetch_exright_events(_client, market, code.strip(), bars[0].day, taipei_today().date())
        result = AdjustedPriceHistory(
            code.strip(), name, market,
            [Adjustment(e.day, e.kind, e.close_before, e.reference, e.factor) for e in events],
            [AdjustedBar(adj.day, adj.open, adj.high, adj.low, adj.close, raw.close, raw.volume)
             for raw, adj in zip(bars, adjust_bars(bars, events), strict=True)],
        )
        lines = [f"【{name}({code}) {market} 還原權息日K {bars[0].day}～{bars[-1].day}】（共 {len(bars)} 個交易日）"]
        if result.adjustments:
            lines.append("還原事件: " + "；".join(
                f"{e.day} {e.kind} 前收 {e.close_before:g} → 參考價 {e.reference:g}（因子 {e.factor:.6f}）"
                for e in result.adjustments
            ))
        else:
            lines.append("期間至今無除權息事件，還原價等於原始價")
        lines.append("")
        for bar in result.bars:
            lines.append(
                f"{bar.day} | 開:{_fmt(bar.open)} 高:{_fmt(bar.high)} 低:{_fmt(bar.low)} 收:{_fmt(bar.close)} | "
                f"原始收盤:{_fmt(bar.raw_close)} | 量:{bar.volume:,.0f}"
            )
        return structured_reply("\n".join(lines), result)

    @mcp.tool(output_schema=output_schema(TechnicalIndicators))
    @handle_api_errors(use_code_param=True)
    def get_technical_indicators(code: str, adjusted: bool = True, days: int = 10) -> ToolResult:
        """計算上市或上櫃股票的技術指標（以最近約半年的日K計算，預設使用還原權息價避免除權息缺口干擾）：
        均線 MA5/10/20/60、KD(9,3,3)、RSI(14)、MACD(12,26,9)、布林通道(20,2)、成交量均量。

        回傳：最新一日各指標數值與相對位置描述（收盤相對均線、K 與 D、DIF 與 MACD 的高低），
        以及最近 days 個交易日的收盤、MA5/MA20、K/D、RSI、DIF/MACD/OSC

        Args:
            code: 股票代號，例如 "2330"、"6488"（自動判斷上市或上櫃）
            adjusted: 是否使用還原權息價（預設 True）
            days: 列出最近幾個交易日的指標（預設 10，最多 60）
        """
        days = max(1, min(days, 60))
        months = months_back(INDICATOR_MONTHS)
        market, name, bars = fetch_daily_bars(_client, code.strip(), months)
        bars = [b for b in bars if None not in (b.high, b.low, b.close)]
        if len(bars) < 30:
            raise ToolError(f"查無 {code} 足夠的上市／上櫃交易資料計算技術指標（僅 {len(bars)} 個交易日）")
        if adjusted:
            bars = adjust_bars(bars, fetch_exright_events(_client, market, code.strip(), bars[0].day, taipei_today().date()))

        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]
        mas = {n: sma(closes, n) for n in MA_PERIODS}
        vol_ma5, vol_ma20 = sma(volumes, 5), sma(volumes, 20)
        k, d = kd(highs, lows, closes)
        rsi14 = rsi(closes, 14)
        dif, sig, osc = macd(closes)
        upper, mid, lower = bollinger(closes)

        result = TechnicalIndicators(code.strip(), name, market, adjusted, bars[0].day, len(bars), [
            IndicatorDay(bars[j].day, closes[j], mas[5][j], mas[10][j], mas[20][j], mas[60][j], k[j], d[j], rsi14[j],
                         dif[j], sig[j], osc[j], upper[j], mid[j], lower[j], volumes[j], vol_ma5[j], vol_ma20[j])
            for j in range(max(0, len(bars) - days), len(bars))
        ])

        last = result.days[-1]
        c = last.close
        ma = {n: getattr(last, f"ma{n}") for n in MA_PERIODS}
        rel = lambda a, b: "高於" if a > b else ("低於" if a < b else "等於")  # noqa: E731
        lines = [
            f"【{name}({code}) {market} 技術指標 {last.day}】（{'還原權息價' if adjusted else '原始價'}，"
            f"樣本 {len(bars)} 個交易日：{bars[0].day}～{last.day}）",
            f"收盤: {_fmt(c)} | " + " | ".join(
                f"MA{n}: {_fmt(ma[n])}（收盤{rel(c, ma[n])}）" if ma[n] is not None else f"MA{n}: -"
                for n in MA_PERIODS
            ),
            f"KD(9): K={_fmt(last.k)} D={_fmt(last.d)}（K{rel(last.k, last.d)}D）| RSI(14): {_fmt(last.rsi14)}",
            f"MACD: DIF={_fmt(last.dif)} MACD={_fmt(last.macd)} OSC={_fmt(last.osc)}"
            + (f"（DIF{rel(last.dif, last.macd)}MACD）" if last.dif is not None and last.macd is not None else ""),
            f"布林(20,2): 上軌 {_fmt(last.bollinger_upper)} / 中軌 {_fmt(last.bollinger_middle)} / "
            f"下軌 {_fmt(last.bollinger_lower)}"
            + (f"（收盤{'在上軌之上' if c > last.bollinger_upper else '在下軌之下' if c < last.bollinger_lower else '在通道內'}）"
               if last.bollinger_upper else ""),
            f"成交量: {last.volume:,.0f} 股 | 5日均量 {_fmt(last.volume_ma5, 0)} | 20日均量 {_fmt(last.volume_ma20, 0)}",
            "",
            f"最近 {days} 個交易日：",
        ]
        for row in result.days:
            lines.append(
                f"{row.day} | 收:{_fmt(row.close)} MA5:{_fmt(row.ma5)} MA20:{_fmt(row.ma20)} | "
                f"K:{_fmt(row.k)} D:{_fmt(row.d)} | RSI:{_fmt(row.rsi14)} | "
                f"DIF:{_fmt(row.dif)} MACD:{_fmt(row.macd)} OSC:{_fmt(row.osc)}"
            )
        return structured_reply("\n".join(lines), result)

