from __future__ import annotations

import os
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
    ) -> None:
        self.account_id = account_id
        self.api_token = api_token
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> CloudflareBrowserClient | None:
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        api_token = os.environ.get("CLOUDFLARE_BROWSER_API_TOKEN") or os.environ.get(
            "CLOUDFLARE_API_TOKEN"
        )
        if not account_id or not api_token:
            return None
        return cls(account_id, api_token)

    def markdown(self, url: str) -> str:
        return self._render("markdown", url)

    def content(self, url: str) -> str:
        return self._render("content", url)

    def _render(self, endpoint: str, url: str) -> str:
        response = httpx.post(
            f"{CLOUDFLARE_API_BASE}/accounts/{self.account_id}/"
            f"browser-rendering/{endpoint}",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json={"url": url},
            timeout=self.timeout,
        )
        response.raise_for_status()
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


def browser_markdown_fetcher_from_environment() -> Callable[[str], str] | None:
    client = CloudflareBrowserClient.from_environment()
    return client.markdown if client else None


def browser_content_fetcher_from_environment() -> Callable[[str], str] | None:
    client = CloudflareBrowserClient.from_environment()
    return client.content if client else None
