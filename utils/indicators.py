"""Technical indicators computed from a daily price series (pure functions, no I/O).

Every function takes values oldest-first and returns a list of the same length, with None
where the indicator is not yet defined (not enough history). Conventions follow what
Taiwanese charting software shows by default: KD(9,3,3) seeded at 50, RSI with Wilder's
smoothing, MACD(12,26,9) with DIF/MACD(signal)/OSC, Bollinger(20, 2σ population).
"""

from math import sqrt
from typing import List, Optional, Sequence, Tuple

Series = List[Optional[float]]


def sma(values: Sequence[float], n: int) -> Series:
    out: Series = []
    window_sum = 0.0
    for i, v in enumerate(values):
        window_sum += v
        if i >= n:
            window_sum -= values[i - n]
        out.append(window_sum / n if i >= n - 1 else None)
    return out


def ema(values: Sequence[float], n: int) -> Series:
    """EMA seeded with the SMA of the first n values."""
    out: Series = [None] * len(values)
    if len(values) < n:
        return out
    k = 2 / (n + 1)
    prev = sum(values[:n]) / n
    out[n - 1] = prev
    for i in range(n, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(closes: Sequence[float], n: int = 14) -> Series:
    """Wilder's RSI."""
    out: Series = [None] * len(closes)
    if len(closes) <= n:
        return out
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains[:n]) / n
    avg_loss = sum(losses[:n]) / n

    def value(g, l):
        return 100.0 if l == 0 else 100 - 100 / (1 + g / l)

    out[n] = value(avg_gain, avg_loss)
    for i in range(n + 1, len(closes)):
        avg_gain = (avg_gain * (n - 1) + gains[i - 1]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i - 1]) / n
        out[i] = value(avg_gain, avg_loss)
    return out


def kd(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
       n: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> Tuple[Series, Series]:
    """Stochastic KD as used in Taiwan: RSV over n days, K = (k-1)/k·K + 1/k·RSV, D likewise, both seeded at 50."""
    k_out: Series = [None] * len(closes)
    d_out: Series = [None] * len(closes)
    k_prev = d_prev = 50.0
    for i in range(n - 1, len(closes)):
        hi = max(highs[i - n + 1:i + 1])
        lo = min(lows[i - n + 1:i + 1])
        rsv = 50.0 if hi == lo else (closes[i] - lo) / (hi - lo) * 100
        k_prev = k_prev * (k_smooth - 1) / k_smooth + rsv / k_smooth
        d_prev = d_prev * (d_smooth - 1) / d_smooth + k_prev / d_smooth
        k_out[i], d_out[i] = k_prev, d_prev
    return k_out, d_out


def macd(closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Series, Series, Series]:
    """Returns (DIF, MACD signal line, OSC histogram)."""
    fast_ema, slow_ema = ema(closes, fast), ema(closes, slow)
    dif: Series = [f - s if f is not None and s is not None else None for f, s in zip(fast_ema, slow_ema)]
    start = next((i for i, v in enumerate(dif) if v is not None), None)
    sig: Series = [None] * len(closes)
    if start is not None:
        tail = ema([v for v in dif[start:]], signal)
        sig[start:] = tail
    osc: Series = [d - s if d is not None and s is not None else None for d, s in zip(dif, sig)]
    return dif, sig, osc


def bollinger(closes: Sequence[float], n: int = 20, width: float = 2.0) -> Tuple[Series, Series, Series]:
    """Returns (upper, middle, lower) bands."""
    mid = sma(closes, n)
    upper: Series = [None] * len(closes)
    lower: Series = [None] * len(closes)
    for i in range(n - 1, len(closes)):
        window = closes[i - n + 1:i + 1]
        sd = sqrt(sum((v - mid[i]) ** 2 for v in window) / n)
        upper[i], lower[i] = mid[i] + width * sd, mid[i] - width * sd
    return upper, mid, lower
