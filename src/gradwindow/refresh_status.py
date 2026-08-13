from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json
from .paths import (
    APPLICATION_SOURCE_STATE_PATH,
    APPLICATIONS_PATH,
    MONITOR_STATE_PATH,
    REFRESH_STATUS_PATH,
)


def generate_refresh_status(
    output_path: Path = REFRESH_STATUS_PATH,
    *,
    applications_path: Path = APPLICATIONS_PATH,
    monitor_state_path: Path = MONITOR_STATE_PATH,
    application_source_state_path: Path = APPLICATION_SOURCE_STATE_PATH,
    completed_at: str | datetime | None = None,
) -> dict[str, str | None]:
    applications = read_json(applications_path).get("meta", {})
    monitor = read_json(monitor_state_path, {}).get("meta", {})
    source_monitor = read_json(application_source_state_path, {}).get("meta", {})
    completed = _iso_timestamp(completed_at)
    payload = {
        "meta": {
            "description": (
                "Truthful freshness markers for published application data and "
                "the last fully successful monitoring pipeline."
            ),
            "updatedAt": completed,
        },
        "dataRefreshedAt": applications.get("updatedAt"),
        "pageCheckedAt": _latest_timestamp(
            monitor.get("checkedAt"), source_monitor.get("checkedAt")
        ),
        "lastSuccessfulMonitoringRun": completed,
    }
    write_json(output_path, payload)
    return payload


def _iso_timestamp(value: str | datetime | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def _latest_timestamp(*values: str | None) -> str | None:
    present = [value for value in values if value]
    return max(present, key=_parse_timestamp, default=None)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
