"""Display helpers for the 分點進出 (broker-branch trading) tools.

Units: the database stores volumes in **shares (股)** so that odd lots keep their
precision, while Taiwanese market convention reads them in **lots (張, 1 lot = 1000
shares)**. Every branch tool therefore renders volumes through :func:`format_lots`;
nothing in ``tools/branch/`` prints a raw share count.

Average prices are always derived from the stored ``buy_amt`` / ``buy_vol`` pair
(Σprice×vol ÷ Σvol), i.e. volume-weighted over whatever period is being summed.
Averaging the per-day averages would weight a 1-lot day the same as a 500-lot day
and is never done here.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional, Sequence, Tuple, Union

SHARES_PER_LOT = 1000

Number = Union[int, float, Decimal, None]

_LOT_QUANTUM = Decimal("0.001")
_PRICE_QUANTUM = Decimal("0.01")
_AMOUNT_QUANTUM = Decimal("1")


def _dec(value: Number) -> Optional[Decimal]:
    """Coerce a DB value to Decimal. psycopg gives int for BIGINT, Decimal for NUMERIC."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def format_lots(shares: Number) -> str:
    """Render a share count as lots (張): 3 decimals, trailing zeros trimmed.

    >>> format_lots(597361)
    '597.361'
    >>> format_lots(356000)
    '356'
    >>> format_lots(1234567890)
    '1,234,567.89'
    >>> format_lots(None)
    '-'
    """
    d = _dec(shares)
    if d is None:
        return "-"
    lots = (d / SHARES_PER_LOT).quantize(_LOT_QUANTUM, rounding=ROUND_HALF_UP)
    sign = "-" if lots < 0 else ""
    lots = abs(lots)
    whole = int(lots)
    frac = (lots - whole).quantize(_LOT_QUANTUM)
    # str(Decimal('0.500')) -> '0.500'; keep the digits after the dot and trim zeros
    digits = str(frac)[2:].rstrip("0")
    out = f"{sign}{whole:,}"
    return f"{out}.{digits}" if digits else out


def format_lots_signed(shares: Number) -> str:
    """Like :func:`format_lots` but always carries a sign, for 買賣超 columns.

    >>> format_lots_signed(558490)
    '+558.49'
    >>> format_lots_signed(-558490)
    '-558.49'
    >>> format_lots_signed(0)
    '0'
    """
    d = _dec(shares)
    if d is None:
        return "-"
    text = format_lots(shares)
    return f"+{text}" if d > 0 else text


def format_amount(amount: Number) -> str:
    """Render a NUMERIC amount in whole TWD with thousands separators."""
    d = _dec(amount)
    if d is None:
        return "-"
    return f"{int(d.quantize(_AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)):,}"


def format_avg_price(amount: Number, volume: Number) -> str:
    """Volume-weighted average price, 2 decimals, or ``-`` when there was no volume.

    ``volume`` of 0 is the normal case for a branch that only bought or only sold,
    so it must render as ``-`` rather than 0 or a ZeroDivisionError.
    """
    amt, vol = _dec(amount), _dec(volume)
    if amt is None or not vol:
        return "-"
    return str((amt / vol).quantize(_PRICE_QUANTUM, rounding=ROUND_HALF_UP))


def format_price(price: Number) -> str:
    """Render a price level as stored (NUMERIC(10,2))."""
    d = _dec(price)
    return "-" if d is None else str(d.quantize(_PRICE_QUANTUM))


def format_date(value: Union[date, datetime, str, None]) -> str:
    """Render a DB date as ``YYYY-MM-DD``."""
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def parse_trade_date(text: str) -> date:
    """Parse a user-supplied trade date.

    Accepts ``YYYY-MM-DD``, ``YYYYMMDD`` and ``YYYY/MM/DD`` (the formats the other
    tools in this server take). Raises :class:`ValueError` with a Chinese message
    that the tool surfaces to the caller.
    """
    raw = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日期格式無法辨識：{text!r}，請用 YYYY-MM-DD 或 YYYYMMDD")


def trailing_streak(nets: Sequence[Number]) -> Tuple[str, int]:
    """Consecutive 買超/賣超 days counting back from the end of ``nets``.

    ``nets`` must be ordered oldest → newest. Returns ``("買", n)``, ``("賣", n)``
    or ``("", 0)``. A day with net 0 ends the streak (it is neither 連買 nor 連賣).

    >>> trailing_streak([-100, 500, 300, 200])
    ('買', 3)
    >>> trailing_streak([500, 0])
    ('', 0)
    """
    values = [_dec(n) for n in nets]
    if not values or not values[-1]:
        return "", 0
    sign = 1 if values[-1] > 0 else -1
    count = 0
    for value in reversed(values):
        if value is None or value == 0 or (value > 0) != (sign > 0):
            break
        count += 1
    return ("買" if sign > 0 else "賣"), count


def sum_field(rows: Iterable[dict], field: str) -> Decimal:
    """Σ of one numeric column across ``rows``, as Decimal (0 when absent/NULL)."""
    total = Decimal(0)
    for row in rows:
        value = _dec(row.get(field))
        if value is not None:
            total += value
    return total
