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
REMINDER_AFTER = timedelta(days=7)
DATA_INTEGRITY_ALERT_TYPES = {
    "catalogue-drop",
    "observed-window-drop",
    "exact-window-drop",
    "programme-id-mismatch",
    "source-cycle-transition",
    "unparsed-source-change",
    "partial-parser-error",
    "unknown-degree-code",
    "programme-record-removed",
}
WARNING_ALERT_TYPES = {
    "PROGRAMME_ID_MISMATCH": "programme-id-mismatch",
    "SOURCE_CYCLE_TRANSITION": "source-cycle-transition",
    "TRANSPORT_ERROR": "partial-transport-error",
    "PARSER_ERROR": "partial-parser-error",
    "UNKNOWN_DEGREE_CODE": "unknown-degree-code",
}
INCIDENT_RESOLUTIONS = {
    "official-source-change",
    "manual-acknowledgement",
}


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
    previous_meta = previous_payload.get("meta", {})
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
    previous_alert_hash = previous_meta.get("activeAlertHash")
    notification_changed = (
        previous_alert_hash is not None and active_alert_hash != previous_alert_hash
    )
    if previous_alert_hash is None and alerts:
        notification_changed = True

    previous_had_alerts = any(
        entry.get("alerts") for entry in previous_entries.values()
    )
    last_notification_at = _parse_datetime(previous_meta.get("lastNotificationAt"))
    if last_notification_at is None and previous_meta.get("notificationChanged"):
        # Legacy health snapshots did not store a reminder timestamp. Their
        # update time corresponds to the issue comment emitted by that run.
        last_notification_at = _parse_datetime(previous_meta.get("updatedAt"))
    notification_due = False
    notification_reason = None
    if alerts:
        if not previous_had_alerts:
            notification_due = True
            notification_reason = "alerts-opened"
        elif (
            last_notification_at is None
            or checked_at - last_notification_at >= REMINDER_AFTER
        ):
            notification_due = True
            notification_reason = "weekly-reminder"
    elif previous_had_alerts:
        notification_due = True
        notification_reason = "alerts-cleared"
    if notification_due:
        last_notification_at = checked_at

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
        "dataIntegrityRisks": len(
            {
                alert["universityId"]
                for alert in alerts
                if alert.get("category") == "data-integrity"
            }
        ),
        "unavailableAdapters": len(
            {
                alert["universityId"]
                for alert in alerts
                if alert.get("category") == "availability"
            }
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
            "notificationDue": notification_due,
            "notificationReason": notification_reason,
            "lastNotificationAt": (
                last_notification_at.isoformat() if last_notification_at else None
            ),
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
    previous_observed = previous.get("observedWindowCount")
    current_observed = int(report.get("observedWindowCount", 0))
    active_incident_baseline = _normalise_incident_baseline(
        previous.get("activeIncidentBaseline")
    )
    if active_incident_baseline:
        baseline_count = active_incident_baseline["catalogProgrammes"]
        baseline_exact = active_incident_baseline["exactWindowCount"]
        baseline_observed = active_incident_baseline["observedWindowCount"]
    else:
        baseline_count = (
            int(previous_count) if previous_count is not None else current_count
        )
        baseline_exact = (
            int(previous_exact) if previous_exact is not None else current_exact
        )
        baseline_observed = (
            int(previous_observed)
            if previous_observed is not None
            else current_observed
        )
    historical_max_count = max(
        int(previous.get("historicalMaxCatalogProgrammes", 0)),
        int(previous.get("baselineCatalogProgrammes", 0)),
        int(previous_count or 0),
        current_count,
    )
    historical_max_exact = max(
        int(previous.get("historicalMaxExactWindowCount", 0)),
        int(previous.get("baselineExactWindowCount", 0)),
        int(previous_exact or 0),
        current_exact,
    )
    historical_max_observed = max(
        int(previous.get("historicalMaxObservedWindowCount", 0)),
        int(previous.get("baselineObservedWindowCount", 0)),
        int(previous_observed or 0),
        current_observed,
    )
    current_cycles = _normalise_cycle_counts(report.get("windowCountsByCycle"))
    previous_cycles = _normalise_cycle_counts(previous.get("windowCountsByCycle"))
    baseline_cycles = (
        active_incident_baseline.get("windowCountsByCycle", {})
        if active_incident_baseline
        else previous_cycles or current_cycles
    )
    historical_max_cycles = _historical_cycle_max(
        _normalise_cycle_counts(previous.get("historicalMaxWindowCountsByCycle")),
        _normalise_cycle_counts(previous.get("baselineWindowCountsByCycle")),
        previous_cycles,
        current_cycles,
    )

    stable_source_hash = previous.get("stableWatchedWindowSourceHash")
    pending_source_hash = previous.get("pendingWatchedWindowSourceHash")
    pending_source_checks = int(previous.get("pendingWatchedWindowSourceChecks", 0))
    current_source_hash = report.get("watchedWindowSourceHash")
    current_source_version = report.get("watchedWindowSourceFingerprintVersion")
    previous_source_version = previous.get("watchedWindowSourceFingerprintVersion")
    unparsed_source_change = previous.get("unparsedSourceChange")
    confirmed_source_change = False
    if current_source_hash:
        if current_source_version != previous_source_version:
            stable_source_hash = current_source_hash
            pending_source_hash = None
            pending_source_checks = 0
            unparsed_source_change = None
        elif not stable_source_hash:
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

    adapter_warnings = list(report.get("adapterWarnings") or [])
    reason_categories = {
        str(warning.get("reason"))
        for warning in adapter_warnings
        if warning.get("reason")
    }
    if int(report.get("missingOpeningDateCount", 0)):
        reason_categories.add("MISSING_OPENING_DATE")
    record_diff = dict(report.get("recordDiff") or {})
    removal_assessment_available = bool(
        report.get(
            "windowRemovalAssessmentAvailable",
            "disappearedWindowDetails" in report,
        )
    )
    disappeared_window_details = dict(report.get("disappearedWindowDetails") or {})
    expired_disappeared_window_ids, future_disappeared_window_ids = (
        _classify_disappeared_windows(disappeared_window_details, checked_at)
    )
    disappeared_programme_ids = record_diff.get("disappearedProgrammeIds") or []
    disappeared_programme_details = dict(
        report.get("disappearedProgrammeDetails") or {}
    )
    (
        expired_disappeared_programme_ids,
        future_disappeared_programme_ids,
        unknown_disappeared_programme_ids,
    ) = _classify_disappeared_programmes(
        disappeared_programme_ids,
        disappeared_programme_details,
        checked_at,
    )
    if (
        future_disappeared_window_ids
        or future_disappeared_programme_ids
        or unknown_disappeared_programme_ids
    ):
        reason_categories.add("SOURCE_RECORD_REMOVED")

    entry = {
        "adapter": report.get("adapter"),
        "sourceUrl": report.get("sourceUrl"),
        "lastAttemptAt": report.get("checkedAt", checked_at.isoformat()),
        "lastSuccessfulAt": report.get("checkedAt", checked_at.isoformat()),
        "consecutiveFailures": 0,
        "catalogueStatus": report.get("catalogueStatus", "ok"),
        "catalogueGranularity": report.get(
            "catalogueGranularity",
            previous.get("catalogueGranularity", "programme-level"),
        ),
        "windowStatus": report.get("windowStatus", "monitoring"),
        "catalogProgrammes": current_count,
        "baselineCatalogProgrammes": baseline_count,
        "historicalMaxCatalogProgrammes": historical_max_count,
        "observedWindowCount": current_observed,
        "baselineObservedWindowCount": baseline_observed,
        "historicalMaxObservedWindowCount": historical_max_observed,
        "exactWindowCount": current_exact,
        "recurringPolicyWindowCount": int(report.get("recurringPolicyWindowCount", 0)),
        "baselineExactWindowCount": baseline_exact,
        "historicalMaxExactWindowCount": historical_max_exact,
        "windowCountsByCycle": current_cycles,
        "baselineWindowCountsByCycle": baseline_cycles,
        "historicalMaxWindowCountsByCycle": historical_max_cycles,
        "missingOpeningDateCount": int(report.get("missingOpeningDateCount", 0)),
        "programmesWithoutDeadlines": int(report.get("programmesWithoutDeadlines", 0)),
        "programmesNeedingReview": int(report.get("programmesNeedingReview", 0)),
        "limitationReason": report.get("limitationReason"),
        "adapterWarnings": adapter_warnings,
        "adapterDiagnostics": dict(report.get("adapterDiagnostics") or {}),
        "reasonCategories": sorted(reason_categories),
        "recordDiff": record_diff,
        "windowRemovalAssessmentAvailable": removal_assessment_available,
        "disappearedWindowDetails": disappeared_window_details,
        "expiredDisappearedWindowIds": expired_disappeared_window_ids,
        "futureDisappearedWindowIds": future_disappeared_window_ids,
        "disappearedProgrammeDetails": disappeared_programme_details,
        "expiredDisappearedProgrammeIds": expired_disappeared_programme_ids,
        "futureDisappearedProgrammeIds": future_disappeared_programme_ids,
        "unknownDisappearedProgrammeIds": unknown_disappeared_programme_ids,
        "windowFingerprint": window_fingerprint,
        "stableWatchedWindowSourceHash": stable_source_hash,
        "watchedWindowSourceFingerprintVersion": current_source_version,
        "pendingWatchedWindowSourceHash": pending_source_hash,
        "pendingWatchedWindowSourceChecks": pending_source_checks,
        "unparsedSourceChange": unparsed_source_change,
        "activeIncidentBaseline": active_incident_baseline or None,
        "incidentOpenedAt": (
            previous.get("incidentOpenedAt") if active_incident_baseline else None
        ),
        "lastKnownGoodWindowCount": int(
            previous.get("lastKnownGoodWindowCount")
            if previous.get("lastKnownGoodWindowCount") is not None
            else baseline_observed
        ),
        "lastIncidentResolution": previous.get("lastIncidentResolution"),
        "lastError": None,
    }
    incident_resolution = str(report.get("incidentResolution") or "")
    incident_acknowledged = bool(
        active_incident_baseline and incident_resolution in INCIDENT_RESOLUTIONS
    )
    regression_active = _count_regression_requires_alert(entry)
    keep_active_incident = bool(
        active_incident_baseline and regression_active and not incident_acknowledged
    )
    if not active_incident_baseline and regression_active:
        active_incident_baseline = _incident_baseline_from_entry(entry)
        entry["activeIncidentBaseline"] = active_incident_baseline
        entry["incidentOpenedAt"] = checked_at.isoformat()
        entry["lastKnownGoodWindowCount"] = baseline_observed
    elif not keep_active_incident:
        _move_baseline_to_current(entry)
        entry["activeIncidentBaseline"] = None
        entry["incidentOpenedAt"] = None
        entry["lastKnownGoodWindowCount"] = current_observed
        if incident_acknowledged:
            entry["lastIncidentResolution"] = {
                "type": incident_resolution,
                "resolvedAt": checked_at.isoformat(),
            }
        elif active_incident_baseline:
            entry["lastIncidentResolution"] = {
                "type": "recovered",
                "resolvedAt": checked_at.isoformat(),
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


def _normalise_incident_baseline(value) -> dict:
    if not isinstance(value, dict):
        return {}
    return {
        "catalogProgrammes": int(value.get("catalogProgrammes", 0)),
        "observedWindowCount": int(value.get("observedWindowCount", 0)),
        "exactWindowCount": int(value.get("exactWindowCount", 0)),
        "windowCountsByCycle": _normalise_cycle_counts(
            value.get("windowCountsByCycle")
        ),
    }


def _incident_baseline_from_entry(entry: dict) -> dict:
    return {
        "catalogProgrammes": int(entry.get("baselineCatalogProgrammes", 0)),
        "observedWindowCount": int(entry.get("baselineObservedWindowCount", 0)),
        "exactWindowCount": int(entry.get("baselineExactWindowCount", 0)),
        "windowCountsByCycle": _normalise_cycle_counts(
            entry.get("baselineWindowCountsByCycle")
        ),
    }


def _move_baseline_to_current(entry: dict) -> None:
    entry["baselineCatalogProgrammes"] = int(entry.get("catalogProgrammes", 0))
    entry["baselineObservedWindowCount"] = int(entry.get("observedWindowCount", 0))
    entry["baselineExactWindowCount"] = int(entry.get("exactWindowCount", 0))
    entry["baselineWindowCountsByCycle"] = _normalise_cycle_counts(
        entry.get("windowCountsByCycle")
    )


def _count_regression_requires_alert(entry: dict) -> bool:
    baseline_count = int(entry.get("baselineCatalogProgrammes", 0))
    current_count = int(entry.get("catalogProgrammes", 0))
    if baseline_count and current_count < baseline_count * CATALOGUE_DROP_RATIO:
        return True

    baseline_exact = int(entry.get("baselineExactWindowCount", 0))
    current_exact = int(entry.get("exactWindowCount", 0))
    if (
        baseline_exact
        and current_exact < baseline_exact
        and _cycle_window_drop_requires_alert(
            entry,
            "exactWindowCount",
            baseline_exact,
            current_exact,
        )
    ):
        return True

    baseline_observed = int(entry.get("baselineObservedWindowCount", 0))
    current_observed = int(entry.get("observedWindowCount", 0))
    return bool(
        baseline_observed
        and current_observed < baseline_observed
        and _cycle_window_drop_requires_alert(
            entry,
            "observedWindowCount",
            baseline_observed,
            current_observed,
        )
    )


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
                "reason": report.get("reason"),
                "message": report.get("message", "Adapter failed"),
                "detectedAt": report.get("checkedAt", checked_at.isoformat()),
            },
            "reasonCategories": ([report["reason"]] if report.get("reason") else []),
        }
    )
    return entry


def _entry_alerts(
    university_id: str,
    entry: dict,
    checked_at: datetime,
) -> list[dict]:
    alerts = []
    for warning in entry.get("adapterWarnings") or []:
        reason = warning.get("reason")
        alert_type = WARNING_ALERT_TYPES.get(reason)
        if not alert_type:
            continue
        warning_alert = _alert(
            university_id,
            alert_type,
            str(warning.get("message") or reason),
            entry,
        )
        warning_alert["reason"] = reason
        warning_alert["sourceUrl"] = warning.get("sourceUrl") or warning_alert.get(
            "sourceUrl"
        )
        warning_alert["details"] = {
            key: value
            for key, value in warning.items()
            if key not in {"reason", "message", "sourceUrl"}
        }
        alerts.append(warning_alert)

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
    stale_success = entry.get("catalogueStatus") == "error" and (
        last_success is None or checked_at - last_success > STALE_AFTER
    )
    if stale_success and failures < FAILURE_ALERT_THRESHOLD:
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
        alert = _alert(
            university_id,
            "catalogue-drop",
            f"Catalogue count fell from baseline {baseline_count} to {current_count}.",
            entry,
        )
        _attach_record_removal_details(alert, entry)
        alerts.append(alert)

    baseline_exact = int(entry.get("baselineExactWindowCount", 0))
    current_exact = int(entry.get("exactWindowCount", 0))
    exact_window_drop = _cycle_window_drop_requires_alert(
        entry,
        "exactWindowCount",
        baseline_exact,
        current_exact,
    )
    if baseline_exact and current_exact < baseline_exact and exact_window_drop:
        alert = _alert(
            university_id,
            "exact-window-drop",
            f"Exact window count fell from baseline {baseline_exact} to {current_exact}.",
            entry,
        )
        _attach_record_removal_details(alert, entry)
        alerts.append(alert)

    baseline_observed = int(entry.get("baselineObservedWindowCount", 0))
    current_observed = int(entry.get("observedWindowCount", 0))
    if (
        baseline_observed
        and current_observed < baseline_observed
        and _cycle_window_drop_requires_alert(
            entry,
            "observedWindowCount",
            baseline_observed,
            current_observed,
        )
    ):
        alert = _alert(
            university_id,
            "observed-window-drop",
            "Observed window count fell from baseline "
            f"{baseline_observed} to {current_observed}.",
            entry,
        )
        _attach_record_removal_details(alert, entry)
        alerts.append(alert)

    risky_disappeared_programmes = [
        *entry.get("futureDisappearedProgrammeIds", []),
        *entry.get("unknownDisappearedProgrammeIds", []),
    ]
    if risky_disappeared_programmes:
        alert = _alert(
            university_id,
            "programme-record-removed",
            (
                f"{len(risky_disappeared_programmes)} programme record(s) "
                "disappeared before their lifecycle could be treated as expired."
            ),
            entry,
        )
        _attach_record_removal_details(alert, entry)
        alerts.append(alert)

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


def _classify_disappeared_windows(
    details: dict[str, dict],
    checked_at: datetime,
) -> tuple[list[str], list[str]]:
    expired = []
    future_or_unknown = []
    today = checked_at.date().isoformat()
    for window_id, detail in sorted(details.items()):
        closes_at = str(detail.get("closesAt") or "")
        if closes_at and closes_at < today:
            expired.append(window_id)
        else:
            future_or_unknown.append(window_id)
    return expired, future_or_unknown


def _classify_disappeared_programmes(
    programme_ids: list[str],
    details: dict[str, dict],
    checked_at: datetime,
) -> tuple[list[str], list[str], list[str]]:
    expired = []
    future = []
    unknown = []
    today = checked_at.date().isoformat()
    for programme_id in sorted(programme_ids):
        detail = details.get(programme_id) or {}
        latest_closes_at = str(detail.get("latestClosesAt") or "")
        if not latest_closes_at:
            unknown.append(programme_id)
        elif latest_closes_at < today:
            expired.append(programme_id)
        else:
            future.append(programme_id)
    return expired, future, unknown


def _window_drop_requires_alert(entry: dict) -> bool:
    if not entry.get("windowRemovalAssessmentAvailable"):
        return True
    return bool(
        entry.get("futureDisappearedWindowIds")
        or entry.get("futureDisappearedProgrammeIds")
        or entry.get("unknownDisappearedProgrammeIds")
    )


def _cycle_window_drop_requires_alert(
    entry: dict,
    metric: str,
    baseline_total: int,
    current_total: int,
) -> bool:
    if current_total >= baseline_total:
        return False
    active_incident = bool(entry.get("activeIncidentBaseline"))
    baseline_cycles = _normalise_cycle_counts(entry.get("baselineWindowCountsByCycle"))
    current_cycles = _normalise_cycle_counts(entry.get("windowCountsByCycle"))
    if not baseline_cycles:
        return active_incident or _window_drop_requires_alert(entry)
    if not current_cycles:
        return active_incident or _window_drop_requires_alert(entry)

    common_cycles = set(baseline_cycles) & set(current_cycles)
    common_cycle_drop = any(
        int(current_cycles[cycle].get(metric, 0))
        < int(baseline_cycles[cycle].get(metric, 0))
        for cycle in common_cycles
    )
    if common_cycle_drop:
        return active_incident or _window_drop_requires_alert(entry)

    # A lower total caused only by replacing one intake cycle with another is
    # a cycle transition, not evidence that the current cycle parser regressed.
    # Record-level future removals still override that safe transition rule.
    return bool(
        entry.get("futureDisappearedWindowIds")
        or entry.get("futureDisappearedProgrammeIds")
        or entry.get("unknownDisappearedProgrammeIds")
    )


def _normalise_cycle_counts(value) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    normalised = {}
    for cycle, raw in value.items():
        if not isinstance(raw, dict):
            continue
        normalised[str(cycle)] = {
            "intakes": sorted(str(item) for item in raw.get("intakes", [])),
            "observedWindowCount": int(raw.get("observedWindowCount", 0)),
            "exactWindowCount": int(raw.get("exactWindowCount", 0)),
            "recurringPolicyWindowCount": int(raw.get("recurringPolicyWindowCount", 0)),
        }
    return normalised


def _historical_cycle_max(*snapshots: dict[str, dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for snapshot in snapshots:
        for cycle, counts in snapshot.items():
            entry = merged.setdefault(
                cycle,
                {
                    "intakes": [],
                    "observedWindowCount": 0,
                    "exactWindowCount": 0,
                    "recurringPolicyWindowCount": 0,
                },
            )
            entry["intakes"] = sorted(
                set(entry["intakes"]) | set(counts.get("intakes", []))
            )
            for metric in (
                "observedWindowCount",
                "exactWindowCount",
                "recurringPolicyWindowCount",
            ):
                entry[metric] = max(entry[metric], int(counts.get(metric, 0)))
    return dict(sorted(merged.items()))


def _attach_record_removal_details(alert: dict, entry: dict) -> None:
    record_diff = entry.get("recordDiff") or {}
    disappeared_windows = record_diff.get("disappearedWindowIds") or []
    disappeared_programmes = record_diff.get("disappearedProgrammeIds") or []
    if not disappeared_windows and not disappeared_programmes:
        return
    alert["reason"] = "SOURCE_RECORD_REMOVED"
    alert["details"] = {
        "disappearedWindowIds": disappeared_windows,
        "disappearedProgrammeIds": disappeared_programmes,
        "previous": record_diff.get("previous"),
        "current": record_diff.get("current"),
        "expiredDisappearedProgrammeIds": entry.get(
            "expiredDisappearedProgrammeIds", []
        ),
        "futureDisappearedProgrammeIds": entry.get("futureDisappearedProgrammeIds", []),
        "unknownDisappearedProgrammeIds": entry.get(
            "unknownDisappearedProgrammeIds", []
        ),
        "disappearedProgrammeDetails": entry.get("disappearedProgrammeDetails", {}),
    }


def _alert(university_id: str, alert_type: str, message: str, entry: dict) -> dict:
    return {
        "id": f"{alert_type}:{university_id}",
        "universityId": university_id,
        "type": alert_type,
        "severity": "maintenance",
        "category": (
            "data-integrity"
            if alert_type in DATA_INTEGRITY_ALERT_TYPES
            else "availability"
        ),
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
        priority = (
            "data integrity"
            if any(alert.get("category") == "data-integrity" for alert in alerts)
            else "availability"
        )
        next_action = _recommended_action(alerts)
        rows.append(
            "| "
            + " | ".join(
                (
                    university_names.get(university_id, university_id),
                    priority,
                    entry.get("catalogueStatus", "unknown"),
                    entry.get("windowStatus", "unknown"),
                    reason.replace("|", "\\|"),
                    next_action,
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
                "| University | Priority | Catalogue | Windows | Reason | Next action | Last success |",
                "|---|---|---|---|---|---|---|",
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
- Published-data risks: {summary["dataIntegrityRisks"]}
- Unavailable adapters: {summary["unavailableAdapters"]}

{maintenance}

Expected `monitoring` status is not an error. The issue body is refreshed after
every full run, while consolidated reminder comments are limited to once every
seven days until all alerts clear.
"""


def _recommended_action(alerts: list[dict]) -> str:
    alert_types = {alert.get("type") for alert in alerts}
    if "exact-window-drop" in alert_types:
        return "Compare the official cycle with parsed windows before publication."
    if "catalogue-drop" in alert_types:
        return "Confirm the official catalogue and repair its endpoint or parser."
    if "unparsed-source-change" in alert_types:
        return "Review the official date signals and update window parsing if needed."
    return "Check source access; update the endpoint or official-domain fallback."
