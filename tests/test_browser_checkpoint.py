from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from gradwindow import browser_cache, browser_rendering
from gradwindow.browser_cache import BrowserCache
from gradwindow.browser_rendering import CloudflareBrowserClient, _retry_after_seconds


def response(status=200, text="official page", headers=None):
    return httpx.Response(status, json=text, headers=headers)


def test_restart_reuses_completed_pages_and_retries_failed_page(tmp_path, monkeypatch):
    calls = []
    broken = True

    def post(*args, **kwargs):
        url = kwargs["json"]["url"]
        calls.append(url)
        return response(503 if broken and url.endswith("2") else 200)

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    first = CloudflareBrowserClient(
        "account",
        "token",
        minimum_interval=0,
        max_retries=0,
        cache=BrowserCache(str(tmp_path)),
    )
    assert first.content("https://ucl.ac.uk/page1") == "official page"
    with pytest.raises(RuntimeError, match="503"):
        first.content("https://ucl.ac.uk/page2")
    broken = False
    resumed = CloudflareBrowserClient(
        "account", "token", minimum_interval=0, cache=BrowserCache(str(tmp_path))
    )
    assert resumed.content("https://ucl.ac.uk/page1") == "official page"
    assert resumed.content("https://ucl.ac.uk/page2") == "official page"
    assert calls == [
        "https://ucl.ac.uk/page1",
        "https://ucl.ac.uk/page2",
        "https://ucl.ac.uk/page2",
    ]


def test_cache_expires_and_never_crosses_utc_day(tmp_path, monkeypatch):
    now = 86400 - 10
    monkeypatch.setattr(browser_cache.time, "time", lambda: now)
    cache = BrowserCache(str(tmp_path), ttl=100)
    cache.put("page", "official")
    now += 9
    assert cache.get("page") == "official"
    now += 2
    assert cache.get("page") is None
    cache.put("page", "new official")
    now += 101
    assert cache.get("page") is None


def test_daily_exhaustion_is_shared_after_restart_but_cached_pages_are_readable(
    tmp_path, monkeypatch
):
    now = 1000.0
    monkeypatch.setattr(browser_cache.time, "time", lambda: now)
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs)
        return response(429, "Browser time limit exceeded for today")

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    cache = BrowserCache(str(tmp_path))
    first = CloudflareBrowserClient("account", "token", minimum_interval=0, cache=cache)
    with pytest.raises(RuntimeError, match="time limit"):
        first.content("https://ucl.ac.uk/a")
    second = CloudflareBrowserClient(
        "account", "token", minimum_interval=0, cache=BrowserCache(str(tmp_path))
    )
    with pytest.raises(RuntimeError, match="deferred"):
        second.content("https://ucl.ac.uk/b")
    assert len(calls) == 1
    now = 86401
    with pytest.raises(RuntimeError, match="time limit"):
        second.content("https://ucl.ac.uk/b")
    assert len(calls) == 2


def test_long_retry_after_defers_without_sleeping(tmp_path, monkeypatch):
    monkeypatch.setattr(
        browser_rendering.httpx,
        "post",
        lambda *a, **kw: response(429, "Rate limit exceeded", {"Retry-After": "300"}),
    )
    client = CloudflareBrowserClient(
        "account",
        "token",
        minimum_interval=0,
        cache=BrowserCache(str(tmp_path)),
        sleep=lambda _: pytest.fail("must defer a long wait"),
    )
    with pytest.raises(RuntimeError, match="429"):
        client.content("https://ucl.ac.uk/a")
    with pytest.raises(RuntimeError, match="deferred"):
        client.content("https://ucl.ac.uk/b")


def test_backoff_grows_without_retry_after(monkeypatch):
    replies = iter([response(429), response(429), response()])
    waits = []
    monkeypatch.setattr(browser_rendering.httpx, "post", lambda *a, **kw: next(replies))
    client = CloudflareBrowserClient(
        "account", "token", minimum_interval=0, sleep=waits.append
    )
    assert client.content("https://ucl.ac.uk/a") == "official page"
    assert waits == [1, 2]


def test_usage_counts_measured_time_and_unknown_headers_separately(
    tmp_path, monkeypatch
):
    cache = BrowserCache(str(tmp_path))
    replies = iter([response(headers={"X-Browser-Ms-Used": "1250"}), response()])
    monkeypatch.setattr(browser_rendering.httpx, "post", lambda *a, **kw: next(replies))
    client = CloudflareBrowserClient(
        "account", "token", minimum_interval=0, cache=cache
    )
    client.content("https://ucl.ac.uk/a")
    client.content("https://ucl.ac.uk/a")
    client.content("https://ucl.ac.uk/b")
    assert cache.summary() == {
        "cache_hits": 1,
        "requests": 2,
        "http_200": 2,
        "measured_browser_ms": 1250,
        "requests_without_usage_header": 1,
    }


def test_cache_key_isolates_options_and_accounts():
    bodies = [
        {"url": "https://ucl.ac.uk/a"},
        {"url": "https://ucl.ac.uk/a?option=A"},
        {"url": "https://ucl.ac.uk/a", "waitForSelector": "article"},
    ]
    keys = {
        BrowserCache.key(account, endpoint, body)
        for account in ("a", "b")
        for endpoint in ("content", "markdown")
        for body in bodies
    }
    assert len(keys) == 12


def test_environment_clients_share_throttle(monkeypatch, tmp_path):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "shared-test")
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", "test")
    monkeypatch.setenv("CLOUDFLARE_BROWSER_CACHE_DIR", str(tmp_path))
    assert (
        CloudflareBrowserClient.from_environment()
        is CloudflareBrowserClient.from_environment()
    )


def test_retry_after_http_date(monkeypatch):
    monkeypatch.setattr(browser_rendering.time, "time", lambda: 0)
    assert (
        _retry_after_seconds(
            response(429, headers={"Retry-After": "Thu, 01 Jan 1970 00:01:00 GMT"}), 10
        )
        == 60
    )


def test_challenge_page_is_not_checkpointed(tmp_path, monkeypatch):
    calls = []

    def post(*a, **kw):
        calls.append(1)
        return response(text="<title>Just a moment</title>")

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    client = CloudflareBrowserClient(
        "account", "token", minimum_interval=0, cache=BrowserCache(str(tmp_path))
    )
    client.content("https://ucl.ac.uk/a")
    client.content("https://ucl.ac.uk/a")
    assert len(calls) == 2


def test_all_browser_workflows_share_queue_and_save_after_failure():
    for name in (
        "discover-programmes.yml",
        "update-data.yml",
        "post-merge-adapter-smoke.yml",
    ):
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "group: application-data-state-writes" in text
        assert "queue: max" in text
        assert "cancel-in-progress: false" in text
        assert "CLOUDFLARE_BROWSER_CACHE_DIR: .cache/browser-fetch" in text
        assert "if: always()\n        with:\n          mode: save" in text


def test_transport_timeout_retries_without_losing_usage_uncertainty(
    tmp_path, monkeypatch
):
    calls = []

    def post(*a, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("timeout")
        return response(headers={"X-Browser-Ms-Used": "20"})

    monkeypatch.setattr(browser_rendering.httpx, "post", post)
    cache = BrowserCache(str(tmp_path))
    client = CloudflareBrowserClient(
        "account", "token", minimum_interval=0, cache=cache, sleep=lambda _: None
    )
    assert client.content("https://ucl.ac.uk/a") == "official page"
    assert cache.summary()["requests"] == 2
    assert cache.summary()["transport_errors"] == 1
    assert cache.summary()["requests_without_usage_header"] == 1


def test_cli_import_does_not_require_optional_sqlite_extension():
    script = """
import builtins
original = builtins.__import__
def without_sqlite(name, *args, **kwargs):
    if name in {"sqlite3", "_sqlite3"}:
        raise ModuleNotFoundError("No module named '_sqlite3'")
    return original(name, *args, **kwargs)
builtins.__import__ = without_sqlite
import gradwindow.cli
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
