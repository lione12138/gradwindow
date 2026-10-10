from __future__ import annotations

import math
import os
import threading
import time
from collections.abc import Callable, Mapping
from email.utils import parsedate_to_datetime

import httpx

from .browser_cache import BrowserCache

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"
_clients: dict[tuple, CloudflareBrowserClient] = {}
_clients_lock = threading.Lock()


class CloudflareBrowserClient:
    """Small REST client for stateless official-page rendering fallbacks."""

    def __init__(
        self,
        account_id: str,
        api_token: str,
        *,
        timeout: float = 60,
        minimum_interval: float = 10,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        cache: BrowserCache | None = None,
    ) -> None:
        self.account_id = account_id
        self.api_token = api_token
        self.timeout = timeout
        self.minimum_interval = max(0, minimum_interval)
        self.max_retries = max(0, max_retries)
        self._sleep = sleep
        self._monotonic = monotonic
        self._request_lock = threading.Lock()
        self._last_request_started_at: float | None = None
        self.cache = cache
        self._blocked_until = 0.0

    @classmethod
    def from_environment(cls) -> CloudflareBrowserClient | None:
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        api_token = os.environ.get("CLOUDFLARE_BROWSER_API_TOKEN") or os.environ.get(
            "CLOUDFLARE_API_TOKEN"
        )
        if not account_id or not api_token:
            return None
        try:
            minimum_interval = float(
                os.environ.get("CLOUDFLARE_BROWSER_MIN_INTERVAL_SECONDS", "10")
            )
        except ValueError:
            minimum_interval = 10
        if not math.isfinite(minimum_interval) or minimum_interval < 0:
            minimum_interval = 10
        directory = os.environ.get("CLOUDFLARE_BROWSER_CACHE_DIR")
        key = (account_id, api_token, minimum_interval, directory)
        with _clients_lock:
            if key not in _clients:
                _clients[key] = cls(
                    account_id,
                    api_token,
                    minimum_interval=minimum_interval,
                    cache=BrowserCache(directory) if directory else None,
                )
            return _clients[key]

    def markdown(self, url: str) -> str:
        return self._render("markdown", url)

    def content(
        self,
        url: str,
        *,
        wait_for_selector: str | None = None,
        script: str | None = None,
    ) -> str:
        return self._render(
            "content",
            url,
            wait_for_selector=wait_for_selector,
            script=script,
        )

    def _render(
        self,
        endpoint: str,
        url: str,
        *,
        wait_for_selector: str | None = None,
        script: str | None = None,
    ) -> str:
        request_body: dict[str, object] = {
            "url": url,
            "rejectResourceTypes": [
                "image",
                "media",
                "font",
                "stylesheet",
            ],
        }
        if wait_for_selector:
            request_body["waitForSelector"] = {
                "selector": wait_for_selector,
                "timeout": 60_000,
                "visible": True,
            }
        if script:
            request_body["addScriptTag"] = [{"content": script}]
        key = BrowserCache.key(self.account_id, endpoint, request_body)
        with self._request_lock:
            if self.cache and (cached := self.cache.get(key)) is not None:
                self.cache.count("cache_hits")
                return cached
            blocked_until = max(
                self._blocked_until,
                self.cache.blocked_until(self.account_id) if self.cache else 0,
            )
            if blocked_until > time.time():
                raise RuntimeError(
                    f"Browser requests deferred until UTC epoch {blocked_until:.0f}; saved pages remain available"
                )
            for attempt in range(self.max_retries + 1):
                self._wait_for_request_slot()
                self._last_request_started_at = self._monotonic()
                if self.cache:
                    self.cache.count("requests")
                try:
                    response = httpx.post(
                        f"{CLOUDFLARE_API_BASE}/accounts/{self.account_id}/"
                        f"browser-rendering/{endpoint}",
                        headers={
                            "Authorization": f"Bearer {self.api_token}",
                            "Content-Type": "application/json",
                        },
                        json=request_body,
                        timeout=self.timeout,
                    )
                except httpx.TransportError:
                    if self.cache:
                        self.cache.count("transport_errors")
                        self.cache.count("requests_without_usage_header")
                    if attempt == self.max_retries:
                        raise
                    self._sleep(min(60, max(1, self.minimum_interval) * 2**attempt))
                    continue
                if self.cache:
                    self.cache.count(f"http_{response.status_code}")
                    try:
                        used = float(response.headers.get("X-Browser-Ms-Used", ""))
                        if not math.isfinite(used) or used < 0:
                            raise ValueError
                    except ValueError:
                        self.cache.count("requests_without_usage_header")
                    else:
                        self.cache.count("measured_browser_ms", used)
                if response.status_code == 429:
                    now = time.time()
                    self._blocked_until = (
                        (int(now // 86400) + 1) * 86400
                        if _daily_limit_exceeded(response)
                        else now
                        + _retry_after_seconds(
                            response, max(1, self.minimum_interval) * 2**attempt
                        )
                    )
                    if self.cache:
                        self.cache.defer(self.account_id, self._blocked_until)
                if not _is_retryable(response):
                    break
                if attempt == self.max_retries:
                    if response.status_code == 429:
                        self._blocked_until = max(self._blocked_until, time.time() + 60)
                        if self.cache:
                            self.cache.defer(self.account_id, self._blocked_until)
                    break
                delay = _retry_after_seconds(
                    response, max(1, self.minimum_interval) * 2**attempt
                )
                if delay > 60:
                    self._blocked_until = max(self._blocked_until, time.time() + delay)
                    if self.cache:
                        self.cache.defer(self.account_id, self._blocked_until)
                    break
                self._sleep(delay)
        if response.is_error:
            raise RuntimeError(_error_message(response))
        payload = response.json()
        if isinstance(payload, str):
            result = payload
        elif (
            isinstance(payload, dict)
            and payload.get("success")
            and isinstance(payload.get("result"), str)
        ):
            result = payload["result"]
        else:
            errors = payload.get("errors") if isinstance(payload, dict) else []
            raise RuntimeError(
                f"Cloudflare Browser Rendering failed: {errors or payload}"
            )
        if (
            self.cache
            and result.strip()
            and not any(
                marker in result.lower()
                for marker in (
                    "<title>just a moment",
                    "cf-chl-",
                    "verify you are human",
                )
            )
        ):
            self.cache.put(key, result)
        return result

    def _wait_for_request_slot(self) -> None:
        if self._last_request_started_at is None or self.minimum_interval <= 0:
            return
        elapsed = self._monotonic() - self._last_request_started_at
        remaining = self.minimum_interval - elapsed
        if remaining > 0:
            self._sleep(remaining)


def _retry_after_seconds(response: httpx.Response, fallback: float) -> float:
    try:
        value = float(response.headers.get("Retry-After", ""))
        if not math.isfinite(value):
            raise ValueError
        return max(0, value)
    except ValueError:
        try:
            return max(
                0,
                parsedate_to_datetime(
                    response.headers.get("Retry-After", "")
                ).timestamp()
                - time.time(),
            )
        except (ValueError, TypeError, OverflowError):
            return max(1, fallback)


def _daily_limit_exceeded(response: httpx.Response) -> bool:
    lowered = response.text.lower()
    return (
        "browser time limit exceeded" in lowered
        or "time limit exceeded for today" in lowered
    )


def _is_retryable(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return not _daily_limit_exceeded(response)
    return response.status_code == 422 or response.status_code >= 500


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        detail = response.text
    else:
        if isinstance(payload, dict):
            detail = str(payload.get("errors") or payload.get("messages") or payload)
        else:
            detail = str(payload)
    detail = " ".join(detail.split())[:300]
    return (
        f"Cloudflare Browser Rendering returned HTTP {response.status_code}: {detail}"
    )


def browser_markdown_fetcher_from_environment() -> Callable[[str], str] | None:
    client = CloudflareBrowserClient.from_environment()
    return client.markdown if client else None


def browser_content_fetcher_from_environment(
    *,
    wait_for_selectors: Mapping[str, str] | None = None,
    scripts: Mapping[str, str] | None = None,
) -> Callable[[str], str] | None:
    client = CloudflareBrowserClient.from_environment()
    if client is None:
        return None

    selectors = dict(wait_for_selectors or {})
    page_scripts = dict(scripts or {})

    def fetch(url: str) -> str:
        return client.content(
            url,
            wait_for_selector=selectors.get(url),
            script=page_scripts.get(url),
        )

    return fetch
