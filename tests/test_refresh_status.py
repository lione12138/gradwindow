from __future__ import annotations

import json
from pathlib import Path

from gradwindow.refresh_status import generate_refresh_status


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_refresh_status_keeps_data_page_and_success_times_distinct(tmp_path) -> None:
    applications = tmp_path / "applications.json"
    monitor = tmp_path / "monitor-state.json"
    source_monitor = tmp_path / "application-source-state.json"
    output = tmp_path / "refresh-status.json"
    _write(applications, {"meta": {"updatedAt": "2026-08-12T06:48:27+00:00"}})
    _write(monitor, {"meta": {"checkedAt": "2026-08-13T05:50:00+00:00"}})
    _write(
        source_monitor,
        {"meta": {"checkedAt": "2026-08-13T06:59:00+00:00"}},
    )

    payload = generate_refresh_status(
        output,
        applications_path=applications,
        monitor_state_path=monitor,
        application_source_state_path=source_monitor,
        completed_at="2026-08-13T07:03:00+00:00",
    )

    assert payload["dataRefreshedAt"] == "2026-08-12T06:48:27+00:00"
    assert payload["pageCheckedAt"] == "2026-08-13T06:59:00+00:00"
    assert payload["lastSuccessfulMonitoringRun"] == "2026-08-13T07:03:00+00:00"
    assert json.loads(output.read_text(encoding="utf-8")) == payload
