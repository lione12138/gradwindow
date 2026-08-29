from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .io import read_json
from .paths import (
    APPLICANT_CATEGORIES_PATH,
    APPLICATION_SOURCE_STATE_PATH,
    APPLICATIONS_PATH,
    COVERAGE_PATH,
    GLOBAL_RANKINGS_PATH,
    MONITOR_STATE_PATH,
    PREDICTIONS_PATH,
    PROGRAMME_ADAPTER_HEALTH_PATH,
    PROGRAMME_GROUPS_PATH,
    PROGRAMS_PATH,
    RECURRING_WINDOWS_PATH,
    REFRESH_STATUS_PATH,
    UNIVERSITIES_PATH,
    WINDOW_POLICIES_PATH,
)

LIVE_RANKINGS = {"the", "arwu"}
UPCOMING_WINDOW_DAYS = 30


class _Dictionary:
    def __init__(self) -> None:
        self.values: list[Any] = []
        self._indexes: dict[str, int] = {}

    def add(self, value: Any) -> int:
        if value in (None, "", [], {}):
            return -1
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in self._indexes:
            self._indexes[key] = len(self.values)
            self.values.append(value)
        return self._indexes[key]


def _application_status(record: dict, today: date) -> str:
    opens_at = date.fromisoformat(record["opensAt"])
    closes_at = date.fromisoformat(record["closesAt"])
    if today > closes_at or (
        record.get("deadlineSemantics") == "before" and today >= closes_at
    ):
        return "closed"
    if today >= opens_at:
        return "open"
    if (opens_at - today).days <= UPCOMING_WINDOW_DAYS:
        return "upcoming"
    return "future"


def _trim_monitor(item: dict | None) -> dict:
    if not item:
        return {}
    return {
        key: item[key]
        for key in ("status", "changed")
        if key in item and item[key] not in (None, False, "")
    }


def _trim_policy(item: dict | None) -> dict | None:
    if not item:
        return None
    guidance = item.get("cycleGuidance") or {}
    return {
        "model": item.get("model"),
        "mastersAvailability": item.get("mastersAvailability"),
        "cycleGuidance": {
            key: guidance[key] for key in ("status", "opensText") if guidance.get(key)
        },
    }


def _trim_coverage(item: dict | None) -> dict | None:
    if not item:
        return None
    return {key: item[key] for key in ("nextAction", "windowCount") if key in item}


def _trim_rankings(payload: dict) -> dict:
    rankings: dict[str, dict] = {}
    for ranking_id, ranking in payload.get("rankings", {}).items():
        available = (
            ranking_id in LIVE_RANKINGS and ranking.get("available") is not False
        )
        rows = []
        if available:
            rows = [
                {
                    key: row[key]
                    for key in (
                        "id",
                        "universityId",
                        "school",
                        "schoolZh",
                        "schoolAliasesZh",
                        "country",
                        "region",
                        "rankPosition",
                        "rankDisplay",
                        "rankingOnly",
                        "sourceUrl",
                    )
                    if key in row
                }
                for row in ranking.get("rows", [])
            ]
        rankings[ranking_id] = {
            key: ranking[key]
            for key in ("label", "shortLabel", "edition", "sourceUrl")
            if ranking.get(key)
        }
        rankings[ranking_id]["available"] = available
        rankings[ranking_id]["rows"] = rows
    return {"rankings": rankings}


def _compact_records(records: list[dict], university_indexes: dict[str, int]) -> dict:
    scopes = _Dictionary()
    intakes = _Dictionary()
    rounds = _Dictionary()
    category_sets = _Dictionary()
    urls = _Dictionary()
    statuses = _Dictionary()
    source_cycles = _Dictionary()
    confidences = _Dictionary()
    monitors = _Dictionary()
    deadline_semantics = _Dictionary()
    trust_statuses = _Dictionary()
    rows: list[list[Any]] = []

    for record in records:
        rows.append(
            [
                record["id"],
                university_indexes[record["universityId"]],
                scopes.add(
                    [
                        record["scopeId"],
                        record["scopeType"],
                        record["program"],
                    ]
                ),
                intakes.add([record["intake"], record.get("intakeDetails") or {}]),
                rounds.add(record.get("round")),
                category_sets.add(record.get("applicantCategories") or []),
                record["opensAt"],
                record["closesAt"],
                urls.add(record.get("applicationUrl")),
                urls.add(record.get("sourceUrl")),
                record.get("verifiedAt"),
                record.get("policyCheckedAt"),
                statuses.add(record["dataStatus"]),
                source_cycles.add(record.get("sourceCycle")),
                confidences.add(record.get("confidence")),
                record.get("evidenceCycleCount"),
                monitors.add(record.get("sourceMonitor") or {}),
                deadline_semantics.add(record.get("deadlineSemantics") or "on"),
                trust_statuses.add(record.get("trustStatus") or "current"),
            ]
        )

    return {
        "version": 3,
        "dictionaries": {
            "scopes": scopes.values,
            "intakes": intakes.values,
            "rounds": rounds.values,
            "categorySets": category_sets.values,
            "urls": urls.values,
            "statuses": statuses.values,
            "sourceCycles": source_cycles.values,
            "confidences": confidences.values,
            "monitors": monitors.values,
            "deadlineSemantics": deadline_semantics.values,
            "trustStatuses": trust_statuses.values,
        },
        "rows": rows,
    }


def build_frontend_payloads(
    today: date | None = None,
    *,
    published_audit: dict | None = None,
) -> tuple[dict, dict, dict[str, dict]]:
    today = today or date.today()
    applications_payload = read_json(APPLICATIONS_PATH)
    universities_payload = read_json(UNIVERSITIES_PATH)
    predictions_payload = read_json(PREDICTIONS_PATH)
    recurring_payload = read_json(RECURRING_WINDOWS_PATH)
    programs_payload = read_json(PROGRAMS_PATH)
    groups_payload = read_json(PROGRAMME_GROUPS_PATH)
    policies_payload = read_json(WINDOW_POLICIES_PATH)
    coverage_payload = read_json(COVERAGE_PATH)
    monitor_payload = read_json(MONITOR_STATE_PATH)
    adapter_health_payload = read_json(
        PROGRAMME_ADAPTER_HEALTH_PATH,
        {"meta": {}},
    )
    source_monitor_payload = read_json(APPLICATION_SOURCE_STATE_PATH)
    refresh_payload = read_json(REFRESH_STATUS_PATH)
    rankings_payload = read_json(GLOBAL_RANKINGS_PATH)
    categories_payload = read_json(APPLICANT_CATEGORIES_PATH)
    trust_statuses = (published_audit or {}).get("recordTrustStatuses", {})

    programs = {item["id"]: item for item in programs_payload.get("programs", [])}
    groups = {item["id"]: item for item in groups_payload.get("groups", [])}
    policies = {
        item["universityId"]: item for item in policies_payload.get("policies", [])
    }
    coverage = {
        item["universityId"]: item for item in coverage_payload.get("universities", [])
    }
    university_monitors = monitor_payload.get("universities", {})
    source_monitors = source_monitor_payload.get("applications", {})

    universities = []
    for item in universities_payload["universities"]:
        university = {
            key: item[key]
            for key in (
                "id",
                "school",
                "schoolZh",
                "schoolAliasesZh",
                "country",
                "region",
                "qsPosition",
                "qsRank",
                "rankDisplay",
                "admissionsDiscovery",
                "admissionsUrl",
                "homepageUrl",
            )
            if key in item
        }
        university["monitor"] = _trim_monitor(university_monitors.get(item["id"]))
        university["windowPolicy"] = _trim_policy(policies.get(item["id"]))
        university["coverage"] = _trim_coverage(coverage.get(item["id"]))
        universities.append(university)

    university_indexes = {item["id"]: index for index, item in enumerate(universities)}

    enriched_records: list[dict] = []
    detail_records: dict[str, list[dict]] = defaultdict(list)
    collections = (
        (applications_payload.get("applications", []), "official"),
        (recurring_payload.get("recurringWindows", []), "recurring"),
        (predictions_payload.get("predictions", []), "predicted"),
    )
    for records, data_status in collections:
        for item in records:
            record = {
                **item,
                "dataStatus": data_status,
                "trustStatus": (
                    trust_statuses.get(item["id"], "current")
                    if data_status == "official"
                    else "current"
                ),
            }
            if item["scopeType"] == "programme":
                program = programs.get(item["scopeId"], {}).get("name")
            elif item["scopeType"] == "programme-group":
                program = groups.get(item["scopeId"], {}).get("name")
            else:
                program = "Institution-level default window"
            record["program"] = program or item["scopeId"]
            monitor_id = item.get("basedOnRecordId") or item["id"]
            record["sourceMonitor"] = _trim_monitor(source_monitors.get(monitor_id))
            enriched_records.append(record)
            details = {
                key: record[key]
                for key in (
                    "id",
                    "evidence",
                    "confidenceReason",
                    "basedOnVerifiedAt",
                    "methodology",
                    "dateBasis",
                    "cycleYearBasis",
                )
                if record.get(key) not in (None, "")
            }
            if len(details) > 1:
                detail_records[record["universityId"]].append(details)

    trusted_records = [
        item for item in enriched_records if item["trustStatus"] == "current"
    ]
    status_counts = Counter(
        _application_status(item, today) for item in trusted_records
    )
    qs_ids = {item["id"] for item in universities if item.get("qsPosition") is not None}
    closed_qs_universities = len(
        {
            item["universityId"]
            for item in trusted_records
            if item["universityId"] in qs_ids
            and _application_status(item, today) == "closed"
        }
    )
    initial_records = [
        item
        for item in enriched_records
        if _application_status(item, today) != "closed"
    ]
    closed_records = [
        item
        for item in enriched_records
        if _application_status(item, today) == "closed"
    ]

    meta = {
        "updatedAt": applications_payload.get("meta", {}).get("updatedAt"),
        "rankingEdition": applications_payload.get("meta", {}).get("rankingEdition"),
        "recordCount": len(universities),
        "qsRecordCount": universities_payload.get("meta", {}).get("qsRecordCount"),
        "officialCount": len(applications_payload.get("applications", [])),
        "trustedOfficialCount": sum(
            trust_statuses.get(item["id"], "current") == "current"
            for item in applications_payload.get("applications", [])
        ),
        "trustStatusCounts": dict(
            Counter(
                trust_statuses.get(item["id"], "current")
                for item in applications_payload.get("applications", [])
            )
        ),
        "predictionCount": len(predictions_payload.get("predictions", [])),
        "recurringCount": len(recurring_payload.get("recurringWindows", [])),
        "statusCounts": dict(status_counts),
        "closedQsUniversityCount": closed_qs_universities,
        "refreshStatus": refresh_payload,
        "monitor": {"meta": monitor_payload.get("meta", {})},
        "adapterHealth": {
            "updatedAt": adapter_health_payload.get("meta", {}).get("updatedAt"),
            "summary": adapter_health_payload.get("meta", {}).get("summary", {}),
        },
    }
    category_labels = {
        item["id"]: {
            "en": item.get("labelEn") or item["id"],
            "zh": item.get("labelZh") or item.get("labelEn") or item["id"],
        }
        for item in categories_payload.get("categories", [])
    }
    index_payload = {
        "meta": meta,
        "universities": universities,
        "rankings": _trim_rankings(rankings_payload),
        "applicantCategoryLabels": category_labels,
        "records": _compact_records(initial_records, university_indexes),
    }
    closed_payload = {
        "meta": {
            "recordCount": len(closed_records),
            "generatedFor": today.isoformat(),
        },
        "records": _compact_records(closed_records, university_indexes),
    }
    details_payload = {
        university_id: {"records": records}
        for university_id, records in detail_records.items()
    }
    return index_payload, closed_payload, details_payload


def write_compact_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
