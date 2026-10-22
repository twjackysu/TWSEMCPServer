"""How long a gateway may reuse an upstream reply."""

from utils.date_helper import taipei_today

# A finished month's trading history never changes; the current month's grows every day.
PAST_MONTH_CACHE_TTL = 3600
CURRENT_MONTH_CACHE_TTL = 120
# A past trading day's report never changes. "Latest" (no date) moves to the next day once the
# evening publication is out, so it is reused for ten minutes only.
PAST_DAY_CACHE_TTL = 3600
LATEST_DAY_CACHE_TTL = 600


def month_cache_ttl(year: int, month: int) -> int:
    """Cache lifetime for a reply covering one calendar month (Taiwan time)."""
    today = taipei_today()
    return CURRENT_MONTH_CACHE_TTL if (year, month) == (today.year, today.month) else PAST_MONTH_CACHE_TTL


def year_cache_ttl(year: int) -> int:
    """Cache lifetime for a reply covering one calendar year (Taiwan time); the current year grows every day."""
    return CURRENT_MONTH_CACHE_TTL if year == taipei_today().year else PAST_MONTH_CACHE_TTL


def day_cache_ttl(date: str) -> int:
    """Cache lifetime for a one-day report requested by YYYYMMDD; "" means the latest day."""
    if not date or date >= f"{taipei_today():%Y%m%d}":
        return LATEST_DAY_CACHE_TTL
    return PAST_DAY_CACHE_TTL
