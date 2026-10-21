"""How long a gateway may reuse an upstream reply."""

from utils.date_helper import taipei_today

# A finished month's trading history never changes; the current month's grows every day.
PAST_MONTH_CACHE_TTL = 3600
CURRENT_MONTH_CACHE_TTL = 120


def month_cache_ttl(year: int, month: int) -> int:
    """Cache lifetime for a reply covering one calendar month (Taiwan time)."""
    today = taipei_today()
    return CURRENT_MONTH_CACHE_TTL if (year, month) == (today.year, today.month) else PAST_MONTH_CACHE_TTL
