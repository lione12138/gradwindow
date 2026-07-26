from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .io import read_json, write_json
from .paths import (
    PROGRAMME_ADAPTER_HEALTH_PATH,
    PROGRAMME_ADAPTER_HEALTH_REPORT_PATH,
    PROGRAMME_CATALOG_STATE_PATH,
    UNIVERSITIES_PATH,
)

FAILURE_ALERT_THRESHOLD = 2
STALE_AFTER = timedelta(hours=48)
CATALOGUE_DROP_RATIO = 0.8


def update_adapter_health(
    reports: list[dict],
    *,
    health_path: Path = PROGRAMME_ADAPTER_HEALTH_PATH,
    report_path: Path = PROGRAMME_ADAPTER_HEALTH_REPORT_PATH,
    catalog_state_path: Path = PROGRAMME_CATALOG_STATE_PATH,
    universities_path: Path = UNIVERSITIES_PATH,
    now: datetime | None = None,
) -> dict:
    """Persist adapter health and render one school-level maintenance digest."""
    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    previous_payload = read_json(
        health_path,
        {"meta": {}, "universities": {}},
    )
    previous_entries = previous_payload.get("universities", {})
    catalog_entries = read_json(
        catalog_state_path,
        {"universities": {}},
    ).get("universities", {})
    university_rows = read_json(universities_path).get("universities", [])
    university_names = {
        item["id"]: item.get("school", item["id"]) for item in university_rows
    }

    entries = {}
    changes: list[dict] = []
    for report in reports:
        university_id = report.get("universityId")
        if not university_id:
            continue
        previous = previous_entries.get(university_id, {})
        catalog_entry = catalog_entries.get(university_id, {})
        if report.get("status") == "ok":
            entry, entry_changes = _successful_entry(
                report,
                previous,
                checked_at,
            )
            changes.extend(
                {"universityId": university_id, **item} for item in entry_changes
            )
        else:
            entry = _failed_entry(report, previous, catalog_entry, checked_at)
        entries[university_id] = entry

    alerts = []
    for university_id, entry in sorted(entries.items()):
        entry_alerts = _entry_alerts(university_id, entry, checked_at)
        entry["healthStatus"] = "needs-maintenance" if entry_alerts else "ok"
        entry["alerts"] = entry_alerts
        alerts.extend(entry_alerts)

    active_alert_hash = _alert_hash(alerts)
    previous_alert_hash = previous_payload.get("meta", {}).get("activeAlertHash")
    notification_changed = (
        previous_alert_hash is not None and active_alert_hash != previous_alert_hash
    )
    if previous_alert_hash is None and alerts:
        notification_changed = True

    summary = {
        "totalAdapters": len(entries),
        "healthyAdapters": sum(
            entry.get("healthStatus") == "ok" for entry in entries.values()
        ),
        "needsMaintenance": len({alert["universityId"] for alert in alerts}),
        "activeAlerts": len(alerts),
        "catalogueErrors": sum(
            entry.get("catalogueStatus") == "error" for entry in entries.values()
        ),
        "monitoringWithoutExactWindows": sum(
            entry.get("windowStatus") == "monitoring" for entry in entries.values()
        ),
        "newExactWindowSchools": sum(
            change.get("type") == "exact-window-increase" for change in changes
        ),
    }
    payload = {
        "meta": {
            "updatedAt": checked_at.isoformat(),
            "description": (
                "Machine-readable dedicated-adapter health and maintenance state. "
                "A lack of published exact dates is monitoring, not an error."
            ),
            "activeAlertHash": active_alert_hash,
            "notificationChanged": notification_changed,
            "summary": summary,
        },
        "universities": entries,
    }
    write_json(health_path, payload)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_health_report(
            payload,
            university_names=university_names,
            changes=changes,
        ),
        encoding="utf-8",
    )
    return payload


def _successful_entry(
    report: dict,
    previous: dict,
    checked_at: datetime,
) -> tuple[dict, list[dict]]:
    current_count = int(report.get("catalogProgrammes", 0))
    current_exact = int(report.get("exactWindowCount", 0))
    previous_count = previous.get("catalogProgrammes")
    if previous_count is None:
        previous_count = report.get("previousCatalogProgrammes")
    previous_exact = previous.get("exactWindowCount")
    baseline_count = max(
        value
        for value in (
            int(previous.get("baselineCatalogProgrammes", 0)),
            int(previous_count or 0),
            current_count,
        )
    )
    baseline_exact = max(
        int(previous.get("baselineExactWindowCount", 0)),
        int(previous_exact or 0),
        current_exact,
    )

    stable_source_hash = previous.get("stableWatchedWindowSourceHash")
    pending_source_hash = previous.get("pendingWatchedWindowSourceHash")
    pending_source_checks = int(previous.get("pendingWatchedWindowSourceChecks", 0))
    current_source_hash = report.get("watchedWindowSourceHash")
    confirmed_source_change = False
    if current_source_hash:
        if not stable_source_hash:
            stable_source_hash = current_source_hash
            pending_source_hash = None
            pending_source_checks = 0
        elif current_source_hash == stable_source_hash:
            pending_source_hash = None
            pending_source_checks = 0
        else:
            if current_source_hash == pending_source_hash:
                pending_source_checks += 1
            else:
                pending_source_hash = current_source_hash
                pending_source_checks = 1
            if pending_source_checks >= 2:
                stable_source_hash = current_source_hash
                pending_source_hash = None
                pending_source_checks = 0
                confirmed_source_change = True

    window_fingerprint = report.get("windowFingerprint")
    unparsed_source_change = previous.get("unparsedSourceChange")
    if unparsed_source_change and window_fingerprint != unparsed_source_change.get(
        "windowFingerprint"
    ):
        unparsed_source_change = None
    if (
        confirmed_source_change
        and previous.get("windowFingerprint") == window_fingerprint
    ):
        unparsed_source_change = {
            "detectedAt": checked_at.isoformat(),
            "sourceHash": stable_source_hash,
            "windowFingerprint": window_fingerprint,
        }

    entry = {
        "adapter": report.get("adapter"),
        "sourceUrl": report.get("sourceUrl"),
        "lastAttemptAt": report.get("checkedAt", checked_at.isoformat()),
        "lastSuccessfulAt": report.get("checkedAt", checked_at.isoformat()),
        "consecutiveFailures": 0,
        "catalogueStatus": report.get("catalogueStatus", "ok"),
        "windowStatus": report.get("windowStatus", "monitoring"),
        "catalogProgrammes": current_count,
        "baselineCatalogProgrammes": baseline_count,
        "observedWindowCount": int(report.get("observedWindowCount", 0)),
        "exactWindowCount": current_exact,
        "baselineExactWindowCount": baseline_exact,
        "missingOpeningDateCount": int(report.get("missingOpeningDateCount", 0)),
        "programmesWithoutDeadlines": int(report.get("programmesWithoutDeadlines", 0)),
        "programmesNeedingReview": int(report.get("programmesNeedingReview", 0)),
        "limitationReason": report.get("limitationReason"),
        "windowFingerprint": window_fingerprint,
        "stableWatchedWindowSourceHash": stable_source_hash,
        "pendingWatchedWindowSourceHash": pending_source_hash,
        "pendingWatchedWindowSourceChecks": pending_source_checks,
        "unparsedSourceChange": unparsed_source_change,
        "lastError": None,
    }
    changes = []
    if previous_exact is not None and current_exact > int(previous_exact):
        changes.append(
            {
                "type": "exact-window-increase",
                "previous": int(previous_exact),
                "current": current_exact,
            }
        )
    if confirmed_source_change:
        changes.append({"type": "confirmed-source-change"})
    return entry, changes


def _failed_entry(
    report: dict,
    previous: dict,
    catalog_entry: dict,
    checked_at: datetime,
) -> dict:
    entry = dict(previous)
    entry.update(
        {
            "adapter": report.get("adapter", previous.get("adapter")),
            "sourceUrl": report.get("sourceUrl", previous.get("sourceUrl")),
            "lastAttemptAt": report.get("checkedAt", checked_at.isoformat()),
            "lastSuccessfulAt": previous.get("lastSuccessfulAt")
            or catalog_entry.get("lastSuccessfulAt")
            or catalog_entry.get("checkedAt"),
            "consecutiveFailures": int(previous.get("consecutiveFailures", 0)) + 1,
            "catalogueStatus": "error",
            "windowStatus": previous.get("windowStatus", "unknown"),
            "lastError": {
                "errorType": report.get("errorType", "Error"),
                "message": report.get("message", "Adapter failed"),
                "detectedAt": report.get("checkedAt", checked_at.isoformat()),
            },
        }
    )
    return entry


def _entry_alerts(
    university_id: str,
    entry: dict,
    checked_at: datetime,
) -> list[dict]:
    alerts = []
    failures = int(entry.get("consecutiveFailures", 0))
    if failures >= FAILURE_ALERT_THRESHOLD:
        message = entry.get("lastError", {}).get("message", "Adapter failed")
        alerts.append(
            _alert(
                university_id,
                "consecutive-failures",
                f"Adapter failed {failures} consecutive checks: {message}",
                entry,
            )
        )

    last_success = _parse_datetime(entry.get("lastSuccessfulAt"))
    if entry.get("catalogueStatus") == "error" and (
        last_success is None or checked_at - last_success > STALE_AFTER
    ):
        alerts.append(
            _alert(
                university_id,
                "stale-success",
                "No successful adapter check has completed in the last 48 hours.",
                entry,
            )
        )

    baseline_count = int(entry.get("baselineCatalogProgrammes", 0))
    current_count = int(entry.get("catalogProgrammes", 0))
    if baseline_count and current_count < baseline_count * CATALOGUE_DROP_RATIO:
        alerts.append(
            _alert(
                university_id,
                "catalogue-drop",
                f"Catalogue count fell from baseline {baseline_count} to {current_count}.",
                entry,
            )
        )

    baseline_exact = int(entry.get("baselineExactWindowCount", 0))
    current_exact = int(entry.get("exactWindowCount", 0))
    if baseline_exact and current_exact < baseline_exact:
        alerts.append(
            _alert(
                university_id,
                "exact-window-drop",
                f"Exact window count fell from baseline {baseline_exact} to {current_exact}.",
                entry,
            )
        )

    if entry.get("unparsedSourceChange"):
        alerts.append(
            _alert(
                university_id,
                "unparsed-source-change",
                (
                    "The official window-watch source changed in two consecutive "
                    "checks, but the parsed window result did not change."
                ),
                entry,
            )
        )
    return alerts


def _alert(university_id: str, alert_type: str, message: str, entry: dict) -> dict:
    return {
        "id": f"{alert_type}:{university_id}",
        "universityId": university_id,
        "type": alert_type,
        "severity": "maintenance",
        "message": message,
        "sourceUrl": entry.get("sourceUrl"),
    }


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _alert_hash(alerts: list[dict]) -> str:
    identity = sorted((alert["universityId"], alert["type"]) for alert in alerts)
    return hashlib.sha256(
        json.dumps(identity, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def render_health_report(
    payload: dict,
    *,
    university_names: dict[str, str],
    changes: list[dict],
) -> str:
    summary = payload["meta"]["summary"]
    alerts_by_university: dict[str, list[dict]] = {}
    for university_id, entry in payload.get("universities", {}).items():
        if entry.get("alerts"):
            alerts_by_university[university_id] = entry["alerts"]

    rows = []
    for university_id, alerts in sorted(alerts_by_university.items()):
        entry = payload["universities"][university_id]
        reason = " ".join(alert["message"] for alert in alerts)
        rows.append(
            "| "
            + " | ".join(
                (
                    university_names.get(university_id, university_id),
                    entry.get("catalogueStatus", "unknown"),
                    entry.get("windowStatus", "unknown"),
                    reason.replace("|", "\\|"),
                    entry.get("lastSuccessfulAt") or "never",
                )
            )
            + " |"
        )

    if rows:
        maintenance = "\n".join(
            (
                "## Maintenance required",
                "",
                "| University | Catalogue | Windows | Reason | Last success |",
                "|---|---|---|---|---|",
                *rows,
            )
        )
    else:
        maintenance = (
            "## Maintenance required\n\n"
            "No adapter currently requires maintainer action."
        )

    changed_schools = sorted(
        {
            change["universityId"]
            for change in changes
            if change.get("type") == "exact-window-increase"
        }
    )
    change_text = (
        ", ".join(university_names.get(item, item) for item in changed_schools)
        if changed_schools
        else "None"
    )
    return f"""# Dedicated adapter health

- Checked adapters: {summary["totalAdapters"]}
- Healthy: {summary["healthyAdapters"]}
- Schools needing maintenance: {summary["needsMaintenance"]}
- Schools monitoring without exact windows: {summary["monitoringWithoutExactWindows"]}
- Schools that gained exact windows: {change_text}

{maintenance}

Expected `monitoring` status is not an error. Notifications are emitted only
when the active school-level alert set changes.
"""
