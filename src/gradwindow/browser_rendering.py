from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable

import httpx

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


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
        return cls(account_id, api_token, minimum_interval=minimum_interval)

    def markdown(self, url: str) -> str:
        return self._render("markdown", url)

    def content(self, url: str) -> str:
        return self._render("content", url)

    def _render(self, endpoint: str, url: str) -> str:
        with self._request_lock:
            for attempt in range(self.max_retries + 1):
                self._wait_for_request_slot()
                self._last_request_started_at = self._monotonic()
                response = httpx.post(
                    f"{CLOUDFLARE_API_BASE}/accounts/{self.account_id}/"
                    f"browser-rendering/{endpoint}",
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "url": url,
                        "rejectResourceTypes": [
                            "image",
                            "media",
                            "font",
                            "stylesheet",
                        ],
                    },
                    timeout=self.timeout,
                )
                if not _is_retryable(response):
                    break
                if attempt == self.max_retries:
                    break
                self._sleep(_retry_after_seconds(response, self.minimum_interval))
        if response.is_error:
            raise RuntimeError(_error_message(response))
        payload = response.json()
        if isinstance(payload, str):
            return payload
        if (
            isinstance(payload, dict)
            and payload.get("success")
            and isinstance(payload.get("result"), str)
        ):
            return payload["result"]
        errors = payload.get("errors") if isinstance(payload, dict) else []
        raise RuntimeError(f"Cloudflare Browser Rendering failed: {errors or payload}")

    def _wait_for_request_slot(self) -> None:
        if self._last_request_started_at is None or self.minimum_interval <= 0:
            return
        elapsed = self._monotonic() - self._last_request_started_at
        remaining = self.minimum_interval - elapsed
        if remaining > 0:
            self._sleep(remaining)


def _retry_after_seconds(response: httpx.Response, fallback: float) -> float:
    try:
        return max(0, float(response.headers.get("Retry-After", "")))
    except ValueError:
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


def browser_content_fetcher_from_environment() -> Callable[[str], str] | None:
    client = CloudflareBrowserClient.from_environment()
    return client.content if client else None
