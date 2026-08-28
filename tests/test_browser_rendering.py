from __future__ import annotations

import httpx

from gradwindow import browser_rendering
from gradwindow.browser_rendering import CloudflareBrowserClient


def _response(status_code: int, *, payload=None, headers=None) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        headers=headers,
        request=httpx.Request("POST", "https://api.cloudflare.test/render"),
    )


def test_browser_client_spaces_quick_action_requests(monkeypatch) -> None:
    now = 0.0
    sleeps: list[float] = []

    def monotonic() -> float:
        return now

    def sleep(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    monkeypatch.setattr(
        browser_rendering.httpx,
        "post",
        lambda *args, **kwargs: _response(200, payload="rendered"),
    )
    client = CloudflareBrowserClient(
        "account",
        "token",
        minimum_interval=10,
        sleep=sleep,
        monotonic=monotonic,
    )

    assert client.content("https://example.com/one") == "rendered"
    assert client.content("https://example.com/two") == "rendered"
    assert sleeps == [10]


def test_browser_client_retries_429_after_server_delay(monkeypatch) -> None:
    responses = iter(
        [
            _response(429, payload={"errors": []}, headers={"Retry-After": "3"}),
            _response(200, payload="rendered"),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(
        browser_rendering.httpx,
        "post",
        lambda *args, **kwargs: next(responses),
    )
    client = CloudflareBrowserClient(
        "account",
        "token",
        minimum_interval=0,
        sleep=sleeps.append,
    )

    assert client.markdown("https://example.com") == "rendered"
    assert sleeps == [3]


def test_browser_client_retries_transient_422_and_blocks_heavy_assets(
    monkeypatch,
) -> None:
    responses = iter(
        [
            _response(422, payload={"errors": [{"message": "navigation timeout"}]}),
            _response(200, payload="rendered"),
        ]
    )
    requests = []
    sleeps: list[float] = []

    def post(*args, **kwargs) -> httpx.Response:
        requests.append(kwargs)
        return next(responses)

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    client = CloudflareBrowserClient(
        "account",
        "token",
        minimum_interval=0,
        sleep=sleeps.append,
    )

    assert client.content("https://example.com") == "rendered"
    assert sleeps == [1]
    assert requests[0]["json"]["rejectResourceTypes"] == [
        "image",
        "media",
        "font",
        "stylesheet",
    ]


def test_browser_client_can_wait_for_a_dynamic_listing_selector(monkeypatch) -> None:
    requests = []

    def post(*args, **kwargs) -> httpx.Response:
        requests.append(kwargs)
        return _response(200, payload="rendered")

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    client = CloudflareBrowserClient("account", "token", minimum_interval=0)

    assert (
        client.content(
            "https://example.com/catalog",
            wait_for_selector="[data-listing] article",
        )
        == "rendered"
    )
    assert requests[0]["json"]["waitForSelector"] == {
        "selector": "[data-listing] article",
        "timeout": 60_000,
        "visible": True,
    }


def test_browser_client_can_inject_a_bounded_listing_script(monkeypatch) -> None:
    requests = []

    def post(*args, **kwargs) -> httpx.Response:
        requests.append(kwargs)
        return _response(200, payload="rendered")

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    client = CloudflareBrowserClient("account", "token", minimum_interval=0)

    assert (
        client.content(
            "https://example.com/catalog",
            script="document.body.dataset.ready = 'true';",
        )
        == "rendered"
    )
    assert requests[0]["json"]["addScriptTag"] == [
        {"content": "document.body.dataset.ready = 'true';"}
    ]


def test_browser_client_does_not_retry_exhausted_daily_quota(monkeypatch) -> None:
    attempts = 0

    def post(*args, **kwargs) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return _response(
            429,
            payload={"errors": [{"message": "Browser time limit exceeded for today"}]},
            headers={"Retry-After": "60"},
        )

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    client = CloudflareBrowserClient(
        "account",
        "token",
        minimum_interval=0,
        sleep=lambda seconds: None,
    )

    try:
        client.content("https://example.com")
    except RuntimeError as exc:
        assert "Browser time limit exceeded for today" in str(exc)
    else:
        raise AssertionError("daily quota exhaustion should remain a hard failure")
    assert attempts == 1
