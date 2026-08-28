from __future__ import annotations

from contextlib import nullcontext

import httpx
import pytest

from gradwindow import http_client


class FakeClient:
    response: httpx.Response
    last_kwargs: dict
    init_count = 0

    def __init__(self, **kwargs) -> None:
        type(self).init_count += 1
        self.kwargs = kwargs
        type(self).last_kwargs = kwargs

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args) -> None:
        return None

    def stream(self, method: str, url: str):
        return nullcontext(self.response)


class IncompleteResponse:
    status_code = 200
    encoding = "utf-8"
    headers = {"content-type": "text/html"}
    url = "https://example.edu"

    @staticmethod
    def iter_bytes():
        raise httpx.RemoteProtocolError("incomplete chunked read")


def test_fetch_page_classifies_blocked_response(monkeypatch) -> None:
    FakeClient.response = httpx.Response(
        403,
        request=httpx.Request("GET", "https://example.edu"),
    )
    monkeypatch.setattr(http_client.httpx, "Client", FakeClient)
    monkeypatch.setattr(http_client, "MIN_HOST_INTERVAL", 0)

    with pytest.raises(http_client.FetchFailure) as caught:
        http_client.fetch_page(
            "https://example.edu",
            user_agent="test",
            attempts=1,
        )
    assert caught.value.kind == "blocked"
    assert caught.value.status_code == 403


def test_fetch_page_returns_response_metadata(monkeypatch) -> None:
    FakeClient.response = httpx.Response(
        200,
        content=b"<main>Applications open</main>",
        headers={"content-type": "text/html; charset=utf-8"},
        request=httpx.Request("GET", "https://example.edu"),
    )
    monkeypatch.setattr(http_client.httpx, "Client", FakeClient)
    monkeypatch.setattr(http_client, "MIN_HOST_INTERVAL", 0)

    page = http_client.fetch_page(
        "https://example.edu",
        user_agent="test",
        attempts=1,
    )
    assert page.status_code == 200
    assert page.body == "<main>Applications open</main>"
    assert page.content_type.startswith("text/html")
    assert page.truncated is False


def test_fetch_page_reuses_a_persistent_client_for_the_same_host(monkeypatch) -> None:
    http_client._close_persistent_clients()
    FakeClient.init_count = 0
    FakeClient.response = httpx.Response(
        200,
        content=b"ok",
        request=httpx.Request("GET", "https://example.edu/one"),
    )
    monkeypatch.setattr(http_client.httpx, "Client", FakeClient)
    monkeypatch.setattr(http_client, "MIN_HOST_INTERVAL", 0)

    http_client.fetch_page("https://example.edu/one", user_agent="session-test")
    http_client.fetch_page("https://example.edu/two", user_agent="session-test")

    assert FakeClient.init_count == 1


def test_fetch_page_merges_extra_headers(monkeypatch) -> None:
    FakeClient.response = httpx.Response(
        200,
        content=b"reader",
        request=httpx.Request("GET", "https://example.edu"),
    )
    monkeypatch.setattr(http_client.httpx, "Client", FakeClient)
    monkeypatch.setattr(http_client, "MIN_HOST_INTERVAL", 0)

    http_client.fetch_page(
        "https://example.edu",
        user_agent="test",
        attempts=1,
        extra_headers={"X-Respond-With": "html", "X-No-Cache": "true"},
    )

    assert FakeClient.last_kwargs["headers"]["X-Respond-With"] == "html"
    assert FakeClient.last_kwargs["headers"]["X-No-Cache"] == "true"


def test_fetch_page_stops_at_byte_limit(monkeypatch) -> None:
    FakeClient.response = httpx.Response(
        200,
        content=b"0123456789",
        request=httpx.Request("GET", "https://example.edu"),
    )
    monkeypatch.setattr(http_client.httpx, "Client", FakeClient)
    monkeypatch.setattr(http_client, "MIN_HOST_INTERVAL", 0)

    page = http_client.fetch_page(
        "https://example.edu",
        user_agent="test",
        max_bytes=5,
        attempts=1,
    )
    assert page.body == "01234"
    assert page.bytes_read == 5
    assert page.truncated is True


def test_fetch_page_classifies_incomplete_body_as_retryable(monkeypatch) -> None:
    FakeClient.response = IncompleteResponse()
    monkeypatch.setattr(http_client.httpx, "Client", FakeClient)
    monkeypatch.setattr(http_client, "MIN_HOST_INTERVAL", 0)

    with pytest.raises(http_client.FetchFailure) as caught:
        http_client.fetch_page(
            "https://example.edu",
            user_agent="test",
            attempts=1,
        )
    assert caught.value.kind == "network"
    assert caught.value.retryable is True


def test_resilient_fetcher_uses_bounded_browser_fallback_for_blocked_html() -> None:
    browser_calls = []

    def blocked(_url: str) -> str:
        raise http_client.FetchFailure(
            "HTTP 403",
            kind="blocked",
            status_code=403,
        )

    fetcher = http_client.ResilientFetcher(
        blocked,
        browser_fetcher=lambda url: browser_calls.append(url) or "<main>ok</main>",
        browser_fallback_limit=1,
    )

    assert fetcher("https://example.edu/programmes") == "<main>ok</main>"
    with pytest.raises(http_client.FetchFailure) as caught:
        fetcher("https://example.edu/another-page")

    assert browser_calls == ["https://example.edu/programmes"]
    assert caught.value.transport_diagnostics["fallbackBudgetExhausted"] == 1
    assert fetcher.diagnostics() == {
        "requests": 2,
        "directSuccesses": 0,
        "directFailures": 2,
        "fallbackEnabled": True,
        "fallbackLimit": 1,
        "fallbackAttempts": 1,
        "fallbackSuccesses": 1,
        "fallbackFailures": 0,
        "fallbackBudgetExhausted": 1,
        "failureKinds": {"blocked": 2},
    }


def test_resilient_fetcher_does_not_browser_render_non_html_documents() -> None:
    browser_calls = []

    def timed_out(_url: str) -> str:
        raise http_client.FetchFailure("timeout", kind="network", retryable=True)

    fetcher = http_client.ResilientFetcher(
        timed_out,
        browser_fetcher=lambda url: browser_calls.append(url) or "rendered",
    )

    with pytest.raises(http_client.FetchFailure):
        fetcher("https://example.edu/catalog.pdf")

    assert browser_calls == []
    assert fetcher.diagnostics()["fallbackAttempts"] == 0


def test_resilient_fetcher_preserves_transport_kind_when_fallback_fails() -> None:
    def rate_limited(_url: str) -> str:
        raise http_client.FetchFailure(
            "HTTP 429",
            kind="rate-limited",
            status_code=429,
            retryable=True,
        )

    fetcher = http_client.ResilientFetcher(
        rate_limited,
        browser_fetcher=lambda _url: (_ for _ in ()).throw(
            RuntimeError("browser quota exhausted")
        ),
    )

    with pytest.raises(http_client.FetchFailure) as caught:
        fetcher("https://example.edu/programmes")

    assert caught.value.kind == "rate-limited"
    assert caught.value.status_code == 429
    assert "browser quota exhausted" in str(caught.value)
    assert caught.value.transport_diagnostics["fallbackFailures"] == 1
