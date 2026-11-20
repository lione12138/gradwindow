from __future__ import annotations

import importlib.util
import json
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest


def load_module():
    path = Path(__file__).parents[1] / "scripts" / "notify_subscribers.py"
    spec = importlib.util.spec_from_file_location("notify_subscribers", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_recently_opened_events_excludes_old_closed_and_untrusted_windows(monkeypatch):
    module = load_module()
    window = {
        "universityId": "example-university",
        "scopeType": "programme",
        "scopeId": "example-programme",
        "opensAt": "2026-11-20",
        "closesAt": "2026-12-01",
        "applicationUrl": "https://example.edu/apply",
        "sourceUrl": "https://example.edu/dates",
    }
    records = [
        {**window, "id": "today"},
        {**window, "id": "yesterday", "opensAt": "2026-11-19"},
        {**window, "id": "old", "opensAt": "2026-11-18"},
        {**window, "id": "future", "opensAt": "2026-11-21"},
        {
            **window,
            "id": "closed",
            "opensAt": "2026-11-19",
            "closesAt": "2026-11-19",
        },
        {
            **window,
            "id": "closes-before-today",
            "opensAt": "2026-11-19",
            "closesAt": "2026-11-20",
            "deadlineSemantics": "before",
        },
        {**window, "id": "needs-review"},
    ]
    files = {
        "applications.json": {"applications": records},
        "universities.json": {
            "universities": [
                {"id": "example-university", "school": "Example University"}
            ]
        },
        "programs.json": {
            "programs": [{"id": "example-programme", "name": "Example Programme"}]
        },
        "programme-groups.json": {"groups": []},
    }
    monkeypatch.setattr(module, "read_json", files.__getitem__)

    events = module.recently_opened_events(
        date(2026, 11, 20), record_trust_statuses={"needs-review": "needs-review"}
    )

    assert [event["id"] for event in events] == ["today", "yesterday"]
    assert all(event["program"] == "Example Programme" for event in events)
    assert all(event["applicationUrl"] == window["applicationUrl"] for event in events)


def test_empty_digest_succeeds_without_service_configuration(monkeypatch, capsys):
    module = load_module()
    monkeypatch.delenv("GRADWINDOW_SUBSCRIBE_URL", raising=False)
    monkeypatch.delenv("GRADWINDOW_NOTIFY_API_KEY", raising=False)

    assert module.notify([])
    assert "No newly opened" in capsys.readouterr().out


def test_notify_http_error_is_reported(
    monkeypatch,
    capsys,
) -> None:
    module = load_module()
    monkeypatch.setenv("GRADWINDOW_SUBSCRIBE_URL", "https://notify.example")
    monkeypatch.setenv("GRADWINDOW_NOTIFY_API_KEY", "bad-key")

    def fake_urlopen(_request, timeout):
        assert timeout == 45
        raise HTTPError(
            "https://notify.example/admin/notify",
            401,
            "Unauthorized",
            {},
            BytesIO(b'{"ok":false}'),
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    ok = module.notify(
        [
            {
                "id": "window-1",
                "school": "Example University",
                "program": "MSc Example",
                "opensAt": "2026-07-01",
                "closesAt": "2026-07-31",
                "applicationUrl": "https://example.edu/apply",
                "sourceUrl": "https://example.edu/source",
            }
        ]
    )

    assert ok is False
    assert "HTTP 401 Unauthorized" in capsys.readouterr().err


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_notify_reports_provider_delivery_failures(monkeypatch, capsys) -> None:
    module = load_module()
    monkeypatch.setenv("GRADWINDOW_SUBSCRIBE_URL", "https://notify.example")
    monkeypatch.setenv("GRADWINDOW_NOTIFY_API_KEY", "shared-key")
    monkeypatch.setattr(
        module,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse({"ok": True, "sent": 1, "failed": 1}),
    )

    ok = module.notify(
        [
            {
                "id": "window-1",
                "school": "Example University",
                "program": "MSc Example",
                "opensAt": "2026-07-01",
                "closesAt": "2026-07-31",
                "applicationUrl": "https://example.edu/apply",
                "sourceUrl": "https://example.edu/source",
            }
        ]
    )

    assert ok is False
    assert "1 deliveries failed" in capsys.readouterr().out


def test_main_exits_nonzero_when_notification_fails(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "recently_opened_events", lambda: [{"id": "window-1"}])
    monkeypatch.setattr(module, "notify", lambda _events: False)
    monkeypatch.setattr(module.sys, "argv", ["notify_subscribers.py"])

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 1


def test_notify_normalizes_bearer_api_key(monkeypatch) -> None:
    module = load_module()
    captured: dict[str, str] = {}

    def fake_urlopen(request, timeout=45):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse({"ok": True, "sent": 1, "failed": 0})

    monkeypatch.setenv("GRADWINDOW_SUBSCRIBE_URL", " https://example.edu/ ")
    monkeypatch.setenv(
        "GRADWINDOW_NOTIFY_API_KEY", "  " + "Bearer " + "demo-token" + " \n"
    )
    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    assert module.notify([{"id": "example-window", "opensAt": "2026-07-10"}]) is True
    assert captured["url"] == "https://example.edu/admin/notify"
    assert captured["authorization"] == "Bearer " + "demo-token"


def test_notify_sends_a_large_event_set_in_one_digest_request(monkeypatch) -> None:
    module = load_module()
    requests: list[list[dict]] = []

    def fake_urlopen(request, timeout=45):
        assert timeout == 45
        requests.append(json.loads(request.data.decode("utf-8"))["events"])
        return FakeResponse({"ok": True, "sent": 1, "failed": 0})

    monkeypatch.setenv("GRADWINDOW_SUBSCRIBE_URL", "https://notify.example")
    monkeypatch.setenv("GRADWINDOW_NOTIFY_API_KEY", "shared-key")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    events = [{"id": f"window-{index}"} for index in range(502)]

    assert module.notify(events) is True
    assert requests == [events]


def test_oversized_digest_is_rejected_before_request(monkeypatch, capsys) -> None:
    module = load_module()

    def unexpected_request(*args, **kwargs):
        pytest.fail("An oversized digest must not make a notification request")

    monkeypatch.setenv("GRADWINDOW_SUBSCRIBE_URL", "https://notify.example")
    monkeypatch.setenv("GRADWINDOW_NOTIFY_API_KEY", "shared-key")
    monkeypatch.setattr(module, "urlopen", unexpected_request)
    events = [{"id": f"window-{index}"} for index in range(1001)]

    assert module.notify(events) is False
    assert "digest limit is 1000" in capsys.readouterr().err
