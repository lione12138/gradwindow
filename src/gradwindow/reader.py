from __future__ import annotations

import threading
import time

from .http_client import fetch_page

READER_USER_AGENT = "GradWindow/1.0"
READER_MIN_INTERVAL = 3.1

_reader_lock = threading.Lock()
_last_reader_request_started_at: float | None = None
_reader_clock = time.monotonic
_reader_sleep = time.sleep


def fetch_reader_page(url: str, *, response_format: str = "content") -> str:
    global _last_reader_request_started_at
    with _reader_lock:
        if _last_reader_request_started_at is not None:
            elapsed = _reader_clock() - _last_reader_request_started_at
            remaining = READER_MIN_INTERVAL - elapsed
            if remaining > 0:
                _reader_sleep(remaining)
        _last_reader_request_started_at = _reader_clock()
        page = fetch_page(
            url,
            user_agent=READER_USER_AGENT,
            timeout=60,
            max_bytes=8_000_000,
            accept="text/plain,text/markdown;q=0.9,*/*;q=0.5",
            extra_headers={
                "X-No-Cache": "true",
                "X-Respond-With": response_format,
                "X-Timeout": "60",
            },
        )
    return page.body


def fetch_reader_html_page(url: str) -> str:
    return fetch_reader_page(url, response_format="html")
