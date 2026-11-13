"""Access to the PostgreSQL database that holds 分點進出 (broker-branch) data.

The database is the one described by ``branch_trades_schema.sql``: ``broker_branches``
and ``brokers`` as reference tables, ``branch_daily_trades`` as the price-level fact
table and ``branch_stock_daily`` as the per-branch-per-stock-per-day rollup, both range
partitioned by ``trade_date``. It is normally a Neon project, but nothing here is
Neon-specific beyond allowing for a cold start.

**Safety.** Every statement run through this module is written in this file or in
``tools/branch/`` and passes its values as bound parameters; no MCP tool accepts SQL
text, and there is deliberately no generic "run this query" tool. The query tools use
``BranchDBConfig.URL`` — point it at a read-only role — and only the backfill tool
calls :meth:`BranchDB.write_transaction`, which uses ``BranchDBConfig.WRITE_URL`` and
falls back to ``URL``.

**Connections.** A ``psycopg_pool.ConnectionPool`` is created lazily per URL with
``min_size=0``, so nothing is held open while the server is idle: a managed Postgres
suspends an idle compute and a pooled connection would be dead by the next call.
``check_connection`` drops a connection that died anyway, and one retry hides the
cold-start failure from the caller.

**Import safety.** ``psycopg`` is imported inside the methods, not at module import,
so a deployment without the driver installed still starts and registers the branch
tools — they then report the failure when called instead of taking the whole server
down at import time.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import BranchDBConfig

logger = logging.getLogger(__name__)

# Bound on the query cache, mirroring APIConfig.RESPONSE_CACHE_MAX_ENTRIES: keys
# include the bound parameters, so without a bound a long-running server would keep
# one entry per distinct query forever.
CACHE_MAX_ENTRIES = 128


class BranchDBNotConfigured(RuntimeError):
    """Raised when no connection string is configured for the branch database."""


class BranchDBUnavailable(RuntimeError):
    """Raised when the database is configured but cannot be reached or queried."""


@dataclass
class Statement:
    """One statement inside a write transaction.

    ``many=True`` means ``params`` is a sequence of parameter sequences and the
    statement runs via ``executemany`` (used for the reference-table upserts, which
    write several hundred rows).
    """

    sql: str
    params: Sequence[Any] = ()
    many: bool = False


@dataclass
class _CacheEntry:
    expires_at: float
    rows: Tuple[Dict[str, Any], ...]


class BranchDB:
    """Query helper for the branch-trades database.

    Instances are cheap: no connection is opened until the first query.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        write_url: Optional[str] = None,
        cache_ttl: Optional[float] = None,
        timeout: Optional[float] = None,
        max_rows: Optional[int] = None,
    ):
        self._url = url if url is not None else BranchDBConfig.URL
        self._write_url = write_url if write_url is not None else BranchDBConfig.WRITE_URL
        self.cache_ttl = BranchDBConfig.CACHE_TTL if cache_ttl is None else cache_ttl
        self.timeout = BranchDBConfig.TIMEOUT if timeout is None else timeout
        self.max_rows = BranchDBConfig.MAX_ROWS if max_rows is None else max_rows
        self._pools: Dict[str, Any] = {}
        self._pool_lock = threading.Lock()
        self._cache: Dict[str, _CacheEntry] = {}
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------ config

    @property
    def configured(self) -> bool:
        """True when a read connection string is set."""
        return bool(self._url)

    @property
    def write_configured(self) -> bool:
        """True when writes are possible (``WRITE_URL``, else ``URL``)."""
        return bool(self._write_url or self._url)

    def _read_url(self) -> str:
        if not self._url:
            raise BranchDBNotConfigured("BRANCH_DB_URL is not set")
        return self._url

    def _write_target(self) -> str:
        url = self._write_url or self._url
        if not url:
            raise BranchDBNotConfigured("BRANCH_DB_WRITE_URL / BRANCH_DB_URL is not set")
        return url

    # -------------------------------------------------------------------- pool

    def _pool(self, url: str):
        with self._pool_lock:
            pool = self._pools.get(url)
            if pool is not None:
                return pool
            try:
                from psycopg.rows import dict_row
                from psycopg_pool import ConnectionPool
            except ImportError as exc:  # driver not installed in this deployment
                raise BranchDBUnavailable(
                    "需要 psycopg 套件才能連線分點資料庫，請執行 `uv sync` 安裝相依套件"
                ) from exc

            pool = ConnectionPool(
                url,
                min_size=0,
                max_size=4,
                timeout=self.timeout,
                # connect_timeout is seconds as an int in libpq
                kwargs={"row_factory": dict_row, "connect_timeout": max(1, int(self.timeout))},
                check=ConnectionPool.check_connection,
                open=True,
                name="branch-db",
            )
            self._pools[url] = pool
            return pool

    def close(self) -> None:
        """Close every pool. Only used by tests and shutdown paths."""
        with self._pool_lock:
            for pool in self._pools.values():
                try:
                    pool.close()
                except Exception:  # pragma: no cover - best effort
                    logger.debug("closing branch-db pool failed", exc_info=True)
            self._pools.clear()

    # ------------------------------------------------------------------- cache

    @staticmethod
    def _cache_key(sql: str, params: Sequence[Any]) -> str:
        return f"{sql}||{params!r}"

    def _cache_get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                self._cache.pop(key, None)
                return None
            # Hand out copies: a caller that sorts or mutates its rows must not
            # corrupt what the next caller reads back.
            return [dict(row) for row in entry.rows]

    def _cache_put(self, key: str, rows: List[Dict[str, Any]], ttl: float) -> None:
        if ttl <= 0:
            return
        with self._cache_lock:
            now = time.monotonic()
            for stale in [k for k, v in self._cache.items() if v.expires_at < now]:
                self._cache.pop(stale, None)
            while len(self._cache) >= CACHE_MAX_ENTRIES:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = _CacheEntry(now + ttl, tuple(dict(row) for row in rows))

    def clear_cache(self) -> None:
        """Drop every cached result (called after a write)."""
        with self._cache_lock:
            self._cache.clear()

    # ------------------------------------------------------------------ queries

    def query(
        self,
        sql: str,
        params: Sequence[Any] = (),
        *,
        cache_ttl: Optional[float] = None,
        max_rows: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run one SELECT and return its rows as dicts.

        ``params`` are bound by the driver, never interpolated. ``max_rows`` caps how
        much is pulled into memory (``BranchDBConfig.MAX_ROWS`` by default); hitting
        the cap is logged, and callers that need exact paging add their own LIMIT.
        """
        ttl = self.cache_ttl if cache_ttl is None else cache_ttl
        cap = self.max_rows if max_rows is None else max_rows
        key = self._cache_key(sql, params)

        cached = self._cache_get(key)
        if cached is not None:
            return cached

        rows = self._execute_read(sql, params, cap)
        self._cache_put(key, rows, ttl)
        return rows

    def query_one(
        self,
        sql: str,
        params: Sequence[Any] = (),
        *,
        cache_ttl: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run one SELECT and return its first row, or None."""
        rows = self.query(sql, params, cache_ttl=cache_ttl, max_rows=1)
        return rows[0] if rows else None

    def _execute_read(self, sql: str, params: Sequence[Any], cap: int) -> List[Dict[str, Any]]:
        url = self._read_url()
        last_error: Optional[Exception] = None
        # Two attempts: a suspended compute refuses or drops the first connection.
        for attempt in (1, 2):
            try:
                with self._pool(url).connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, tuple(params))
                        rows = cur.fetchmany(cap + 1)
                if len(rows) > cap:
                    logger.warning(
                        "branch-db query hit the %d row cap; results were truncated", cap
                    )
                    rows = rows[:cap]
                return [dict(row) for row in rows]
            except BranchDBUnavailable:
                raise
            except Exception as exc:
                last_error = exc
                if attempt == 1 and self._is_transient(exc):
                    logger.info("branch-db query failed (%s); retrying once", exc)
                    continue
                break
        raise BranchDBUnavailable(f"分點資料庫查詢失敗: {last_error}") from last_error

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        """True for errors a second attempt can plausibly fix (cold start, dropped conn)."""
        try:
            import psycopg
        except ImportError:  # pragma: no cover - _pool would already have raised
            return False
        return isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError))

    # ------------------------------------------------------------------- writes

    def write_transaction(self, statements: Sequence[Statement]) -> List[int]:
        """Run ``statements`` in one transaction and return each one's rowcount.

        Used only by the backfill tool. The whole batch commits or rolls back
        together, so a half-applied reference table is not a possible outcome.
        """
        url = self._write_target()
        counts: List[int] = []
        with self._pool(url).connection() as conn:
            with conn.cursor() as cur:
                for stmt in statements:
                    if stmt.many:
                        cur.executemany(stmt.sql, [tuple(p) for p in stmt.params])
                    else:
                        cur.execute(stmt.sql, tuple(stmt.params))
                    counts.append(cur.rowcount)
        self.clear_cache()
        return counts


_instance: Optional[BranchDB] = None
_instance_lock = threading.Lock()


def get_branch_db() -> BranchDB:
    """Process-wide :class:`BranchDB`, created on first use."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = BranchDB()
    return _instance
