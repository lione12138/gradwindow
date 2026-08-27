from __future__ import annotations

from calendar import monthrange
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from .io import read_json, write_json
from .paths import (
    APPLICATIONS_PATH,
    PROGRAMME_ADAPTER_HEALTH_PATH,
    PROGRAMME_CATALOG_STATE_PATH,
    PUBLISHED_DATA_AUDIT_PATH,
    PUBLISHED_DATA_AUDIT_REPORT_PATH,
)

DEADLINE_AFTER_INTAKE_TOLERANCE = timedelta(days=45)
FLEXIBLE_ENTRY_MARKERS = (
    "flexible entry",
    "multiple start dates",
    "multiple dates",
    "rolling admission",
    "rolling application",
)
RECONCILED_FIELDS = ("opensAt", "closesAt", "sourceUrl")


def audit_published_data(
    applications: list[dict],
    *,
    catalog_state: dict[str, dict] | None = None,
    adapter_health: dict[str, dict] | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    catalog_state = catalog_state or {}
    adapter_health = adapter_health or {}
    issues = []

    for item in applications:
        if issue := _suspicious_intake_issue(item):
            issues.append(issue)

    for item in applications:
        university_id = item.get("universityId")
        health = adapter_health.get(university_id, {})
        state = catalog_state.get(university_id, {})
        if (
            item.get("scopeType") != "programme"
            or health.get("healthStatus") != "ok"
            or not isinstance(state.get("windows"), dict)
            or date.fromisoformat(item["closesAt"]) < today
        ):
            continue
        snapshot = state["windows"]
        identity = _published_window_identity(item)
        current = snapshot.get(identity)
        if current is None:
            issues.append(
                {
                    "type": "published-record-missing-from-snapshot",
                    "universityId": university_id,
                    "recordId": item["id"],
                    "intake": item["intake"],
                    "closesAt": item["closesAt"],
                    "sourceUrl": item["sourceUrl"],
                    "snapshotIdentity": identity,
                    "lastSuccessfulAdapterCheck": health.get("lastSuccessfulAt")
                    or state.get("lastSuccessfulAt")
                    or state.get("checkedAt"),
                    "recommendedAction": "retire-or-correct-review",
                    "seoDisposition": "quarantine",
                }
            )
            continue
        differences = {
            field: {"published": item.get(field), "snapshot": current.get(field)}
            for field in RECONCILED_FIELDS
            if item.get(field) != current.get(field)
        }
        if differences:
            issues.append(
                {
                    "type": "published-record-changed-from-snapshot",
                    "universityId": university_id,
                    "recordId": item["id"],
                    "intake": item["intake"],
                    "closesAt": item["closesAt"],
                    "sourceUrl": item["sourceUrl"],
                    "snapshotIdentity": identity,
                    "differences": differences,
                    "lastSuccessfulAdapterCheck": health.get("lastSuccessfulAt")
                    or state.get("lastSuccessfulAt")
                    or state.get("checkedAt"),
                    "recommendedAction": "correct-published-record-review",
                    "seoDisposition": "quarantine",
                }
            )

    issues.sort(
        key=lambda item: (
            item["universityId"],
            item["recordId"],
            item["type"],
        )
    )
    issue_counts = Counter(item["type"] for item in issues)
    quarantined_ids = sorted(
        {item["recordId"] for item in issues if item["seoDisposition"] == "quarantine"}
    )
    return {
        "generatedFor": today.isoformat(),
        "summary": {
            "issues": len(issues),
            "universitiesNeedingReview": len({item["universityId"] for item in issues}),
            "quarantinedRecords": len(quarantined_ids),
            "suspiciousIntakeWindows": issue_counts["suspicious-intake-window"],
            "publishedRecordsMissingFromSnapshot": issue_counts[
                "published-record-missing-from-snapshot"
            ],
            "publishedRecordsChangedFromSnapshot": issue_counts[
                "published-record-changed-from-snapshot"
            ],
        },
        "quarantinedRecordIds": quarantined_ids,
        "issues": issues,
    }


def generate_published_data_audit(
    *,
    applications_path: Path = APPLICATIONS_PATH,
    catalog_state_path: Path = PROGRAMME_CATALOG_STATE_PATH,
    adapter_health_path: Path = PROGRAMME_ADAPTER_HEALTH_PATH,
    output_path: Path = PUBLISHED_DATA_AUDIT_PATH,
    report_path: Path = PUBLISHED_DATA_AUDIT_REPORT_PATH,
    today: date | None = None,
) -> dict:
    payload = audit_published_data(
        read_json(applications_path).get("applications", []),
        catalog_state=read_json(
            catalog_state_path,
            {"universities": {}},
        ).get("universities", {}),
        adapter_health=read_json(
            adapter_health_path,
            {"universities": {}},
        ).get("universities", {}),
        today=today,
    )
    write_json(output_path, payload)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_published_data_audit(payload), encoding="utf-8")
    return payload


def render_published_data_audit(payload: dict) -> str:
    summary = payload["summary"]
    rows = []
    for issue in payload["issues"]:
        rows.append(
            "- `{record}` — **{kind}** ({university}, {intake}, closes {closes}) — "
            "{action}".format(
                record=issue["recordId"],
                kind=issue["type"],
                university=issue["universityId"],
                intake=issue["intake"],
                closes=issue["closesAt"],
                action=issue["recommendedAction"],
            )
        )
    issue_rows = "\n".join(rows) or "- No active published-data issues."
    return f"""# Published data audit

Generated for {payload["generatedFor"]}.

- Active issues: {summary["issues"]}
- Universities needing review: {summary["universitiesNeedingReview"]}
- Records quarantined from SEO aggregates: {summary["quarantinedRecords"]}
- Suspicious intake/deadline mappings: {summary["suspiciousIntakeWindows"]}
- Published records missing from a healthy current snapshot: {summary["publishedRecordsMissingFromSnapshot"]}
- Published records changed from a healthy current snapshot: {summary["publishedRecordsChangedFromSnapshot"]}

## Maintenance queue

{issue_rows}
"""


def _suspicious_intake_issue(item: dict) -> dict | None:
    details = item.get("intakeDetails") or {}
    cycle_year = details.get("cycleYear")
    start_month = details.get("startMonth")
    if not cycle_year or not start_month or _has_flexible_entry_exception(item):
        return None
    intake_month_end = date(
        int(cycle_year),
        int(start_month),
        monthrange(int(cycle_year), int(start_month))[1],
    )
    cutoff = intake_month_end + DEADLINE_AFTER_INTAKE_TOLERANCE
    closes_at = date.fromisoformat(item["closesAt"])
    if closes_at <= cutoff:
        return None
    return {
        "type": "suspicious-intake-window",
        "universityId": item["universityId"],
        "recordId": item["id"],
        "intake": item["intake"],
        "nominalIntakeMonth": f"{int(cycle_year):04d}-{int(start_month):02d}",
        "closesAt": item["closesAt"],
        "toleranceCutoff": cutoff.isoformat(),
        "sourceUrl": item["sourceUrl"],
        "recommendedAction": "correct-intake-or-document-flexible-entry",
        "seoDisposition": "quarantine",
    }


def _has_flexible_entry_exception(item: dict) -> bool:
    text = " ".join(
        str(item.get(field) or "") for field in ("intake", "round", "evidence")
    ).lower()
    return any(marker in text for marker in FLEXIBLE_ENTRY_MARKERS)


def _published_window_identity(item: dict) -> str:
    categories = ",".join(sorted(item.get("applicantCategories", []))) or "all"
    return "::".join(
        (
            item["scopeId"],
            item["intake"],
            item.get("round", ""),
            categories,
        )
    )
