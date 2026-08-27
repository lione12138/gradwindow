from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt
from tenacity.wait import wait_exponential_jitter

DEFAULT_TIMEOUT = 20.0
DEFAULT_MAX_BYTES = 1_500_000
MIN_HOST_INTERVAL = 0.15
DEFAULT_BROWSER_FALLBACK_LIMIT = 3
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

_rate_lock = threading.Lock()
_host_locks: dict[str, threading.Lock] = {}
_last_request_by_host: dict[str, float] = {}


@dataclass(slots=True)
class FetchedPage:
    body: str
    raw_bytes: bytes
    final_url: str
    status_code: int
    content_type: str
    charset: str
    bytes_read: int
    truncated: bool


class FetchFailure(Exception):
    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.retryable = retryable


class ResilientFetcher:
    """Bounded browser fallback around the shared retrying HTTP transport."""

    def __init__(
        self,
        direct_fetcher: Callable[[str], str],
        *,
        browser_fetcher: Callable[[str], str] | None = None,
        browser_fallback_limit: int = DEFAULT_BROWSER_FALLBACK_LIMIT,
    ) -> None:
        self.direct_fetcher = direct_fetcher
        self.browser_fetcher = browser_fetcher
        self.browser_fallback_limit = max(0, browser_fallback_limit)
        self._lock = threading.Lock()
        self._requests = 0
        self._direct_successes = 0
        self._direct_failures = 0
        self._fallback_attempts = 0
        self._fallback_successes = 0
        self._fallback_failures = 0
        self._fallback_budget_exhausted = 0
        self._failure_kinds: Counter[str] = Counter()

    def __call__(self, url: str) -> str:
        with self._lock:
            self._requests += 1
        try:
            content = self.direct_fetcher(url)
        except Exception as direct_error:
            kind = _fetch_failure_kind(direct_error)
            with self._lock:
                self._direct_failures += 1
                self._failure_kinds[kind] += 1
            if not self._reserve_browser_fallback(url, direct_error):
                self._attach_diagnostics(direct_error)
                raise
            try:
                rendered = self.browser_fetcher(url) if self.browser_fetcher else ""
                if not rendered or not rendered.strip():
                    raise RuntimeError("browser fallback returned an empty response")
            except Exception as browser_error:
                with self._lock:
                    self._fallback_failures += 1
                failure = _combined_fallback_failure(direct_error, browser_error)
                self._attach_diagnostics(failure)
                raise failure from browser_error
            with self._lock:
                self._fallback_successes += 1
            return rendered
        with self._lock:
            self._direct_successes += 1
        return content

    def diagnostics(self) -> dict[str, object]:
        with self._lock:
            return {
                "requests": self._requests,
                "directSuccesses": self._direct_successes,
                "directFailures": self._direct_failures,
                "fallbackEnabled": self.browser_fetcher is not None,
                "fallbackLimit": self.browser_fallback_limit,
                "fallbackAttempts": self._fallback_attempts,
                "fallbackSuccesses": self._fallback_successes,
                "fallbackFailures": self._fallback_failures,
                "fallbackBudgetExhausted": self._fallback_budget_exhausted,
                "failureKinds": dict(sorted(self._failure_kinds.items())),
            }

    def _reserve_browser_fallback(
        self,
        url: str,
        error: Exception,
    ) -> bool:
        if (
            self.browser_fetcher is None
            or not _browser_fallback_eligible(url, error)
            or self.browser_fallback_limit == 0
        ):
            return False
        with self._lock:
            if self._fallback_attempts >= self.browser_fallback_limit:
                self._fallback_budget_exhausted += 1
                return False
            self._fallback_attempts += 1
            return True

    def _attach_diagnostics(self, error: Exception) -> None:
        try:
            error.transport_diagnostics = self.diagnostics()
        except (AttributeError, TypeError):
            return


def _fetch_failure_kind(error: Exception) -> str:
    if isinstance(error, FetchFailure):
        return error.kind
    return type(error).__name__


def _browser_fallback_eligible(url: str, error: Exception) -> bool:
    if not isinstance(error, FetchFailure) or error.kind not in {
        "blocked",
        "rate-limited",
        "network",
        "server",
    }:
        return False
    path = urlparse(url).path.lower()
    return not path.endswith((".csv", ".json", ".pdf", ".xls", ".xlsx", ".xml", ".zip"))


def _combined_fallback_failure(
    direct_error: Exception,
    browser_error: Exception,
) -> FetchFailure:
    direct_message = " ".join(str(direct_error).split())[:180]
    browser_message = " ".join(str(browser_error).split())[:180]
    return FetchFailure(
        "Direct retrieval and browser fallback failed: "
        f"direct={direct_message}; browser={browser_message}",
        kind=_fetch_failure_kind(direct_error),
        status_code=(
            direct_error.status_code if isinstance(direct_error, FetchFailure) else None
        ),
    )


def _wait_for_host(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return
    with _rate_lock:
        host_lock = _host_locks.setdefault(host, threading.Lock())
    with host_lock:
        now = time.monotonic()
        wait_for = MIN_HOST_INTERVAL - (now - _last_request_by_host.get(host, 0))
        if wait_for > 0:
            time.sleep(wait_for)
        _last_request_by_host[host] = time.monotonic()


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, FetchFailure) and exc.retryable


def _fetch_once(
    url: str,
    *,
    user_agent: str,
    timeout: float,
    max_bytes: int,
    accept: str,
    extra_headers: Mapping[str, str] | None,
) -> FetchedPage:
    _wait_for_host(url)
    try:
        request_headers = {
            "User-Agent": user_agent,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        request_headers.update(extra_headers or {})
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
            headers=request_headers,
        ) as client:
            with client.stream("GET", url) as response:
                status = response.status_code
                if status in {401, 403}:
                    raise FetchFailure(
                        f"HTTP {status}",
                        kind="blocked",
                        status_code=status,
                    )
                if status == 429:
                    raise FetchFailure(
                        "HTTP 429",
                        kind="rate-limited",
                        status_code=status,
                        retryable=True,
                    )
                if 500 <= status <= 599:
                    raise FetchFailure(
                        f"HTTP {status}",
                        kind="server",
                        status_code=status,
                        retryable=True,
                    )
                if status >= 400:
                    raise FetchFailure(
                        f"HTTP {status}",
                        kind="http",
                        status_code=status,
                    )

                chunks = bytearray()
                truncated = False
                for chunk in response.iter_bytes():
                    remaining = max_bytes - len(chunks)
                    if remaining <= 0:
                        truncated = True
                        break
                    chunks.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        truncated = True
                        break
                charset = response.encoding or "utf-8"
                return FetchedPage(
                    body=bytes(chunks).decode(charset, errors="replace"),
                    raw_bytes=bytes(chunks),
                    final_url=str(response.url),
                    status_code=status,
                    content_type=response.headers.get("content-type", ""),
                    charset=charset,
                    bytes_read=len(chunks),
                    truncated=truncated,
                )
    except (
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
    ) as exc:
        raise FetchFailure(
            str(exc),
            kind="network",
            retryable=True,
        ) from exc
    except httpx.HTTPError as exc:
        raise FetchFailure(str(exc), kind="client") from exc


def fetch_page(
    url: str,
    *,
    user_agent: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    attempts: int = 3,
    accept: str = "text/html,application/xhtml+xml",
    extra_headers: Mapping[str, str] | None = None,
) -> FetchedPage:
    retrying = Retrying(
        retry=retry_if_exception(_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=0.5, max=8),
        reraise=True,
    )
    return retrying(
        _fetch_once,
        url,
        user_agent=user_agent,
        timeout=timeout,
        max_bytes=max_bytes,
        accept=accept,
        extra_headers=extra_headers,
    )
