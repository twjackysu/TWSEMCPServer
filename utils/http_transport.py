"""How requests reach upstream: one pooled session per site, TLS policy, and polite retries.

``TWSEAPIClient`` decides when a request may go out (per-site throttle, caches, single-flight);
this module decides how it is sent.

- **Connection reuse.** One ``requests.Session`` per site (``throttle_key``), so repeated calls
  reuse TCP/TLS connections instead of a new handshake each time. A site's requests already go
  out one at a time under its throttle lock, so its session is never used by two threads at once.
  Cookies are cleared after every request: calls stay as stateless as with ``requests.request``.
- **TLS.** Every site is fully verified. Checked 2026-10-21 under Python 3.13, whose default
  context adds ``VERIFY_X509_STRICT``: all 13 upstream hosts pass except ``cpx.cbc.gov.tw``, whose
  certificate lacks a Subject Key Identifier. Sites in ``NON_STRICT_X509_SITES`` keep chain and
  hostname verification and only drop the strict RFC 5280 extras.
- **Retries.** See ``UpstreamRetry``.
"""

import ssl
from typing import cast

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.connectionpool import ConnectionPool
from urllib3.exceptions import InvalidHeader, MaxRetryError, ResponseError
from urllib3.util.retry import Retry

# Sites (throttle_key) whose certificate chain verifies but fails VERIFY_X509_STRICT.
NON_STRICT_X509_SITES = frozenset({"cbc.gov.tw"})

# Second retry waits RETRY_BACKOFF_FACTOR * 2 seconds (the first waits UpstreamRetry.MIN_BACKOFF).
RETRY_BACKOFF_FACTOR = 1.0
# Random extra wait added to each retry so that retries never line up into a burst.
RETRY_JITTER = 0.5


class UpstreamRetry(Retry):
    """Retry a transient failure up to twice, without crowding the upstream.

    - Only gateway errors (502/503/504), connection failures, and 413/429/503 that carry a
      ``Retry-After`` are retried. Read timeouts are not: the upstream may still be working on it.
    - Every retry waits at least ``MIN_BACKOFF`` (urllib3 retries the first failure at once),
      then 2 s, plus jitter. Retries run inside the site's throttle lock, so nothing else hits that
      site in the meantime.
    - A ``Retry-After`` longer than ``MAX_RETRY_AFTER`` ends the retries instead of holding the
      site's lock for minutes; the caller then reports the 429/503 as a failure.
    """

    MIN_BACKOFF = 1.0
    MAX_RETRY_AFTER = 10.0

    def get_backoff_time(self) -> float:
        return max(self.MIN_BACKOFF, super().get_backoff_time())

    def increment(self, method=None, url=None, response=None, error=None, _pool=None, _stacktrace=None):
        header = response.headers.get("Retry-After") if response is not None else None
        if header is not None:
            try:
                wait = self.parse_retry_after(header)
            except InvalidHeader:
                wait = 0.0
            if wait > self.MAX_RETRY_AFTER:
                # urllib3's own Retry.increment raises with the same _pool, which may be None.
                raise MaxRetryError(cast(ConnectionPool, _pool), url, ResponseError(
                    f"upstream asked to retry after {header}s (more than {self.MAX_RETRY_AFTER:g}s); not retrying"))
        return super().increment(method, url, response, error, _pool, _stacktrace)


def upstream_retry() -> UpstreamRetry:
    return UpstreamRetry(
        total=2, connect=2, read=0, status=2, other=0,
        status_forcelist=(502, 503, 504),
        # Every POST here submits a read-only query form (TAIFEX downloads, MOPS, SITCA).
        allowed_methods=frozenset({"GET", "POST"}),
        backoff_factor=RETRY_BACKOFF_FACTOR,
        backoff_jitter=RETRY_JITTER,
        respect_retry_after_header=True,
        # After the last retry, hand back the response; the client's raise_for_status reports it.
        raise_on_status=False,
    )


class _NonStrictX509Adapter(HTTPAdapter):
    """Verifies chain and hostname, without Python 3.13's VERIFY_X509_STRICT extras."""

    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context(cafile=certifi.where())
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def new_site_session(site: str, verify: bool = True) -> requests.Session:
    """A pooled session for one site, with its TLS policy and retry rules mounted.

    ``verify=False`` (the TWSE_VERIFY_SSL escape hatch) needs the plain adapter: a context that
    checks hostnames cannot be combined with requests' CERT_NONE.
    """
    non_strict = verify and site in NON_STRICT_X509_SITES
    adapter_class = _NonStrictX509Adapter if non_strict else HTTPAdapter
    adapter = adapter_class(max_retries=upstream_retry())
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
