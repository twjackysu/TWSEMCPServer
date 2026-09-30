"""還原權息股價 and 技術指標 for one listed or OTC stock, computed from the exchanges' daily
prices and ex-rights results (see utils/price_series.py)."""

from datetime import date
from typing import Optional
from fastmcp import FastMCP
from utils import TWSEAPIClient, handle_api_errors
from utils.date_helper import taipei_today
from utils.indicators import bollinger, kd, macd, rsi, sma
from utils.price_series import adjust_bars, fetch_daily_bars, fetch_exright_events, months_back

MAX_MONTHS = 12
# 60-day MA and MACD(26+9) need ~90 trading days of history before the first shown value.
INDICATOR_MONTHS = 7
MA_PERIODS = (5, 10, 20, 60)


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

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_adjusted_price_history(code: str, start_month: str = "", end_month: str = "") -> str:
        """查詢上市或上櫃股票的「還原權息」日K：把除權息造成的價格缺口還原，才能正確比較長期漲跌與報酬。
        以證交所／櫃買中心公告的除權息參考價計算還原因子（參考價÷除權息前收盤價），往前回溯調整。

        Args:
            code: 股票代號，例如 "2330"、"6488"（自動判斷上市或上櫃）
            start_month: 起始月份 YYYYMM（選填，預設最近 3 個月）
            end_month: 結束月份 YYYYMM（選填，預設同 start_month）。區間最多 12 個月

        Returns:
            每個交易日的還原開高低收、原始收盤價、成交量（股），以及期間內套用的除權息事件與還原因子
        """
        end, count = parse_months(start_month.strip(), end_month.strip())
        if isinstance(end, str):
            return end
        months = months_back(count, date(*end, 1) if end else None)
        market, name, bars = fetch_daily_bars(_client, code.strip(), months)
        if not bars:
            return f"查無 {code} 在 {months[0][0]}-{months[0][1]:02d}～{months[-1][0]}-{months[-1][1]:02d} 的上市／上櫃交易資料"

        # 還原要考慮查詢區間之後到今天的除權息，否則較早的價格會少乘後面的因子
        events = fetch_exright_events(_client, market, code.strip(), bars[0].day, taipei_today().date())
        adjusted = adjust_bars(bars, events)
        lines = [f"【{name}({code}) {market} 還原權息日K {bars[0].day}～{bars[-1].day}】（共 {len(bars)} 個交易日）"]
        if events:
            lines.append("還原事件: " + "；".join(
                f"{e.day} {e.kind} 前收 {e.close_before:g} → 參考價 {e.reference:g}（因子 {e.factor:.6f}）" for e in events
            ))
        else:
            lines.append("期間至今無除權息事件，還原價等於原始價")
        lines.append("")
        for raw, adj in zip(bars, adjusted):
            lines.append(
                f"{adj.day} | 開:{_fmt(adj.open)} 高:{_fmt(adj.high)} 低:{_fmt(adj.low)} 收:{_fmt(adj.close)} | "
                f"原始收盤:{_fmt(raw.close)} | 量:{raw.volume:,.0f}"
            )
        return "\n".join(lines)

    @mcp.tool
    @handle_api_errors(use_code_param=True)
    def get_technical_indicators(code: str, adjusted: bool = True, days: int = 10) -> str:
        """計算上市或上櫃股票的技術指標（以最近約半年的日K計算，預設使用還原權息價避免除權息缺口干擾）：
        均線 MA5/10/20/60、KD(9,3,3)、RSI(14)、MACD(12,26,9)、布林通道(20,2)、成交量均量。

        Args:
            code: 股票代號，例如 "2330"、"6488"（自動判斷上市或上櫃）
            adjusted: 是否使用還原權息價（預設 True）
            days: 列出最近幾個交易日的指標（預設 10，最多 60）

        Returns:
            最新一日各指標數值與相對位置描述（收盤相對均線、K 與 D、DIF 與 MACD 的高低），
            以及最近 days 個交易日的收盤、MA5/MA20、K/D、RSI、DIF/MACD/OSC
        """
        days = max(1, min(days, 60))
        months = months_back(INDICATOR_MONTHS)
        market, name, bars = fetch_daily_bars(_client, code.strip(), months)
        bars = [b for b in bars if None not in (b.high, b.low, b.close)]
        if len(bars) < 30:
            return f"查無 {code} 足夠的上市／上櫃交易資料計算技術指標（僅 {len(bars)} 個交易日）"
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

        i = len(bars) - 1
        c = closes[i]
        rel = lambda a, b: "高於" if a > b else ("低於" if a < b else "等於")  # noqa: E731
        lines = [
            f"【{name}({code}) {market} 技術指標 {bars[i].day}】（{'還原權息價' if adjusted else '原始價'}，"
            f"樣本 {len(bars)} 個交易日：{bars[0].day}～{bars[i].day}）",
            f"收盤: {_fmt(c)} | " + " | ".join(
                f"MA{n}: {_fmt(mas[n][i])}（收盤{rel(c, mas[n][i])}）" if mas[n][i] is not None else f"MA{n}: -"
                for n in MA_PERIODS
            ),
            f"KD(9): K={_fmt(k[i])} D={_fmt(d[i])}（K{rel(k[i], d[i])}D）| RSI(14): {_fmt(rsi14[i])}",
            f"MACD: DIF={_fmt(dif[i])} MACD={_fmt(sig[i])} OSC={_fmt(osc[i])}"
            + (f"（DIF{rel(dif[i], sig[i])}MACD）" if dif[i] is not None and sig[i] is not None else ""),
            f"布林(20,2): 上軌 {_fmt(upper[i])} / 中軌 {_fmt(mid[i])} / 下軌 {_fmt(lower[i])}"
            + (f"（收盤{'在上軌之上' if c > upper[i] else '在下軌之下' if c < lower[i] else '在通道內'}）" if upper[i] else ""),
            f"成交量: {volumes[i]:,.0f} 股 | 5日均量 {_fmt(vol_ma5[i], 0)} | 20日均量 {_fmt(vol_ma20[i], 0)}",
            "",
            f"最近 {days} 個交易日：",
        ]
        for j in range(max(0, len(bars) - days), len(bars)):
            lines.append(
                f"{bars[j].day} | 收:{_fmt(closes[j])} MA5:{_fmt(mas[5][j])} MA20:{_fmt(mas[20][j])} | "
                f"K:{_fmt(k[j])} D:{_fmt(d[j])} | RSI:{_fmt(rsi14[j])} | "
                f"DIF:{_fmt(dif[j])} MACD:{_fmt(sig[j])} OSC:{_fmt(osc[j])}"
            )
        return "\n".join(lines)

