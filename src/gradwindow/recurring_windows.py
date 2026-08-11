from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .discovery import same_official_domain
from .intakes import with_intake_details
from .io import read_json, write_json
from .paths import (
    APPLICATIONS_PATH,
    PROGRAMME_CANDIDATES_PATH,
    PROGRAMME_CATALOG_STATE_PATH,
    PROGRAMS_PATH,
    RECURRING_WINDOWS_PATH,
    UNIVERSITIES_PATH,
)
from .predictions import official_cycle_key

DATE_BASIS = "official-recurring-policy"
CYCLE_YEAR_BASIS = "system-materialized-next-cycle"
PUBLIC_DISCLAIMER = (
    "The official university page publishes a recurring day-and-month application "
    "policy. GradWindow maps that policy to the next applicable cycle year; the year "
    "is not a cycle-specific date announced by the university."
)


def generate_recurring_windows(
    output_path: Path = RECURRING_WINDOWS_PATH,
    *,
    universities_path: Path = UNIVERSITIES_PATH,
    programs_path: Path = PROGRAMS_PATH,
    applications_path: Path = APPLICATIONS_PATH,
    candidates_path: Path = PROGRAMME_CANDIDATES_PATH,
    state_path: Path = PROGRAMME_CATALOG_STATE_PATH,
    today: str | date | None = None,
) -> dict[str, int]:
    generated_on = _iso_date(today) if today is not None else date.today().isoformat()
    universities = read_json(universities_path).get("universities", [])
    programs = read_json(programs_path).get("programs", [])
    applications = read_json(applications_path).get("applications", [])
    candidates = read_json(candidates_path, {"items": []}).get("items", [])
    state = read_json(state_path, {"universities": {}}).get("universities", {})

    domains_by_university = {
        item["id"]: item.get("officialDomains", []) for item in universities
    }
    programs_by_id = {item["id"]: item for item in programs}
    official_keys = {official_cycle_key(item) for item in applications}
    recurring_keys: set[tuple] = set()
    records: list[dict] = []
    suppressed = 0

    for candidate in candidates:
        if candidate.get("type") not in {
            "known-programme-recurring-policy",
            "known-programme-window-guidance",
        }:
            continue
        if candidate.get("status") == "rejected":
            continue
        programme_payload = candidate.get("programme") or {}
        programme_id = programme_payload.get("id")
        programme = programs_by_id.get(programme_id)
        if programme is None:
            continue
        university_id = programme["universityId"]
        if candidate.get("universityId") != university_id:
            continue
        official_domains = domains_by_university.get(university_id, [])

        for window in candidate.get("windows") or []:
            if window.get("opensAtBasis") != DATE_BASIS:
                continue
            if not all(window.get(key) for key in ("intake", "opensAt", "closesAt")):
                continue
            source_url = window.get("sourceUrl") or candidate.get("sourceUrl")
            if not same_official_domain(source_url, official_domains):
                continue
            application_url = programme_payload.get("applicationUrl") or programme.get(
                "applicationUrl"
            )
            if not application_url:
                continue
            record = with_intake_details(
                {
                    "id": _record_id(programme_id, window),
                    "universityId": university_id,
                    "scopeType": "programme",
                    "scopeId": programme_id,
                    "intake": window["intake"],
                    "round": window.get("round") or "",
                    "applicantCategories": window.get("applicantCategories") or ["all"],
                    "opensAt": window["opensAt"],
                    "closesAt": window["closesAt"],
                    "applicationUrl": application_url,
                    "sourceUrl": source_url,
                    "policyCheckedAt": _checked_at(
                        state.get(university_id), candidate, generated_on
                    ),
                    "dateBasis": DATE_BASIS,
                    "cycleYearBasis": CYCLE_YEAR_BASIS,
                    "evidence": candidate.get("evidenceExcerpt") or PUBLIC_DISCLAIMER,
                }
            )
            key = official_cycle_key(record)
            if key in official_keys:
                suppressed += 1
                continue
            if key in recurring_keys:
                continue
            recurring_keys.add(key)
            records.append(record)

    records.sort(
        key=lambda item: (
            item["opensAt"],
            item["closesAt"],
            item["universityId"],
            item["scopeId"],
            item["id"],
        )
    )
    write_json(
        output_path,
        {
            "meta": {
                "title": "Official recurring application policies",
                "updatedAt": generated_on,
                "recordCount": len(records),
                "dataStatus": DATE_BASIS,
                "disclaimer": PUBLIC_DISCLAIMER,
            },
            "recurringWindows": records,
        },
    )
    return {
        "recurringPolicyWindows": len(records),
        "universities": len({item["universityId"] for item in records}),
        "suppressedByOfficialRecords": suppressed,
    }


def _record_id(programme_id: str, window: dict) -> str:
    parts = (
        "recurring",
        programme_id,
        str(window.get("intake") or "cycle"),
        str(window.get("round") or "main"),
        "-".join(sorted(window.get("applicantCategories") or ["all"])),
    )
    return _slug("-".join(parts))


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _checked_at(state: object, candidate: dict, fallback: str) -> str:
    if isinstance(state, dict) and state.get("checkedAt"):
        return _iso_date(state["checkedAt"])
    if candidate.get("detectedAt"):
        return _iso_date(candidate["detectedAt"])
    return fallback


def _iso_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]
