from __future__ import annotations

from types import SimpleNamespace

from gradwindow import reader


def test_reader_fetcher_uses_service_user_agent(monkeypatch) -> None:
    request = {}

    def fetch_page(url: str, **kwargs):
        request.update(url=url, **kwargs)
        return SimpleNamespace(body="reader text")

    monkeypatch.setattr(reader, "fetch_page", fetch_page)
    monkeypatch.setattr(reader, "_last_reader_request_started_at", None)

    assert reader.fetch_reader_page("https://r.jina.ai/http://example.com") == (
        "reader text"
    )
    assert request["user_agent"] == "GradWindow/1.0"
    assert request["timeout"] == 60
    assert request["max_bytes"] == 8_000_000
    assert request["extra_headers"] == {
        "X-No-Cache": "true",
        "X-Respond-With": "content",
        "X-Timeout": "60",
    }


def test_reader_html_fetcher_requests_complete_uncached_html(monkeypatch) -> None:
    request = {}

    def fetch_page(url: str, **kwargs):
        request.update(url=url, **kwargs)
        return SimpleNamespace(body="<html>complete</html>")

    monkeypatch.setattr(reader, "fetch_page", fetch_page)
    monkeypatch.setattr(reader, "_last_reader_request_started_at", None)

    assert reader.fetch_reader_html_page("https://r.jina.ai/http://example.com") == (
        "<html>complete</html>"
    )
    assert request["extra_headers"]["X-Respond-With"] == "html"
    assert request["extra_headers"]["X-No-Cache"] == "true"


def test_reader_fetcher_spaces_anonymous_requests(monkeypatch) -> None:
    now = 0.0
    sleeps: list[float] = []

    def clock() -> float:
        return now

    def sleep(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    monkeypatch.setattr(reader, "_reader_clock", clock)
    monkeypatch.setattr(reader, "_reader_sleep", sleep)
    monkeypatch.setattr(reader, "_last_reader_request_started_at", None)
    monkeypatch.setattr(
        reader,
        "fetch_page",
        lambda *args, **kwargs: SimpleNamespace(body="reader text"),
    )

    reader.fetch_reader_page("https://r.jina.ai/http://example.com/one")
    reader.fetch_reader_page("https://r.jina.ai/http://example.com/two")

    assert sleeps == [reader.READER_MIN_INTERVAL]
