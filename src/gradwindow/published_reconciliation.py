from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from .io import read_json, write_json
from .paths import (
    APPLICATION_SOURCE_STATE_PATH,
    APPLICATIONS_PATH,
    PROGRAMME_ADAPTER_HEALTH_PATH,
    PROGRAMME_CATALOG_STATE_PATH,
    PUBLISHED_RECONCILIATION_CANDIDATES_PATH,
)
from .published_data_audit import audit_published_data

ISSUE_ACTIONS = {
    "published-record-changed-from-snapshot": "date-change-review",
    "published-record-missing-from-snapshot": "retire-review",
    "published-record-source-url-changed": "safe-source-url-update",
    "suspicious-intake-window": "intake-mismatch-review",
}
ACTION_PRIORITY = {
    "safe-source-url-update": 0,
    "intake-mismatch-review": 1,
    "retire-review": 2,
    "date-change-review": 3,
}


def reconcile_published(
    *,
    university_id: str | None = None,
    dry_run: bool = False,
    applications_path: Path = APPLICATIONS_PATH,
    catalog_state_path: Path = PROGRAMME_CATALOG_STATE_PATH,
    adapter_health_path: Path = PROGRAMME_ADAPTER_HEALTH_PATH,
    source_state_path: Path = APPLICATION_SOURCE_STATE_PATH,
    candidates_path: Path = PUBLISHED_RECONCILIATION_CANDIDATES_PATH,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    applications = read_json(applications_path).get("applications", [])
    if university_id:
        applications = [
            item for item in applications if item.get("universityId") == university_id
        ]
    catalog_state = read_json(catalog_state_path, {"universities": {}}).get(
        "universities", {}
    )
    adapter_health = read_json(adapter_health_path, {"universities": {}}).get(
        "universities", {}
    )
    source_state = read_json(source_state_path, {"applications": {}}).get(
        "applications", {}
    )
    audit = audit_published_data(
        applications,
        catalog_state=catalog_state,
        adapter_health=adapter_health,
        source_state=source_state,
        today=today,
    )
    issues_by_record: dict[str, list[dict]] = {}
    for issue in audit["issues"]:
        issues_by_record.setdefault(issue["recordId"], []).append(issue)

    applications_by_id = {item["id"]: item for item in applications}
    candidates = [
        _candidate_for_record(applications_by_id[record_id], issues, today)
        for record_id, issues in sorted(issues_by_record.items())
    ]
    compared = [
        item
        for item in applications
        if _is_reconciliation_eligible(item, catalog_state, adapter_health, today)
    ]
    issue_counts = Counter(issue["type"] for issue in audit["issues"])
    compared_issue_ids = {
        issue["recordId"]
        for issue in audit["issues"]
        if issue["type"].startswith("published-record-")
    }
    result = {
        "generatedFor": today.isoformat(),
        "universityId": university_id,
        "summary": {
            "universities": len({item["universityId"] for item in compared}),
            "recordsCompared": len(compared),
            "unchanged": len(compared) - len(compared_issue_ids),
            "deadlineChanged": issue_counts["published-record-changed-from-snapshot"],
            "disappeared": issue_counts["published-record-missing-from-snapshot"],
            "sourceUrlOnlyChanged": issue_counts["published-record-source-url-changed"],
            "intakeMismatches": issue_counts["suspicious-intake-window"],
            "candidates": len(candidates),
        },
        "candidates": candidates,
    }
    if not dry_run:
        _write_candidates(
            candidates_path,
            candidates,
            university_id=university_id,
            generated_for=today.isoformat(),
        )
    return result


def render_reconciliation_summary(result: dict) -> str:
    summary = result["summary"]
    scope = result.get("universityId") or "All universities"
    return "\n".join(
        (
            scope,
            f"records compared: {summary['recordsCompared']}",
            f"unchanged: {summary['unchanged']}",
            f"deadline changed: {summary['deadlineChanged']}",
            f"disappeared: {summary['disappeared']}",
            f"source URL only changed: {summary['sourceUrlOnlyChanged']}",
            f"intake mismatches: {summary['intakeMismatches']}",
            f"review candidates: {summary['candidates']}",
        )
    )


def _candidate_for_record(item: dict, issues: list[dict], today: date) -> dict:
    issue_types = sorted(issue["type"] for issue in issues)
    differences = {}
    for issue in issues:
        differences.update(issue.get("differences", {}))
    proposed_changes = {
        field: difference.get("snapshot")
        for field, difference in sorted(differences.items())
    }
    actions = [ISSUE_ACTIONS[issue_type] for issue_type in issue_types]
    action = max(actions, key=ACTION_PRIORITY.__getitem__)
    fingerprint_payload = {
        "recordId": item["id"],
        "issueTypes": issue_types,
        "differences": differences,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "id": f"published-reconciliation:{item['id']}:{fingerprint[:12]}",
        "type": "published-reconciliation",
        "action": action,
        "status": "pending",
        "universityId": item["universityId"],
        "recordId": item["id"],
        "detectedAt": today.isoformat(),
        "issueTypes": issue_types,
        "differences": differences,
        "proposedChanges": proposed_changes,
        "sourceUrl": item["sourceUrl"],
        "recommendedActions": sorted({issue["recommendedAction"] for issue in issues}),
        "fingerprint": fingerprint,
    }


def _is_reconciliation_eligible(
    item: dict,
    catalog_state: dict[str, dict],
    adapter_health: dict[str, dict],
    today: date,
) -> bool:
    state = catalog_state.get(item.get("universityId"), {})
    health = adapter_health.get(item.get("universityId"), {})
    return (
        item.get("scopeType") == "programme"
        and health.get("healthStatus") == "ok"
        and isinstance(state.get("windows"), dict)
        and date.fromisoformat(item["closesAt"]) >= today
    )


def _write_candidates(
    path: Path,
    candidates: list[dict],
    *,
    university_id: str | None,
    generated_for: str,
) -> None:
    existing = read_json(path, {"meta": {}, "candidates": []})
    existing_candidates = existing.get("candidates", [])
    existing_by_id = {item["id"]: item for item in existing_candidates}
    refreshed = []
    for candidate in candidates:
        previous = existing_by_id.get(candidate["id"])
        if previous and previous.get("status") != "pending":
            candidate = {**candidate, **previous}
        refreshed.append(candidate)

    retained = [
        item
        for item in existing_candidates
        if item.get("status") != "pending"
        or (university_id and item.get("universityId") != university_id)
    ]
    retained_ids = {item["id"] for item in retained}
    merged = retained + [item for item in refreshed if item["id"] not in retained_ids]
    merged.sort(key=lambda item: (item.get("universityId", ""), item["id"]))
    write_json(
        path,
        {
            "meta": {
                "updatedFor": generated_for,
                "description": (
                    "Published-window reconciliation candidates generated from "
                    "healthy official adapter snapshots."
                ),
            },
            "candidates": merged,
        },
    )
