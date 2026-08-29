from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json
from .paths import (
    APPLICATIONS_PATH,
    COVERAGE_PATH,
    GLOBAL_RANKINGS_PATH,
    PREDICTIONS_PATH,
    PROGRAMS_PATH,
    UNIVERSITIES_PATH,
    WINDOW_POLICIES_PATH,
)

TOP_LIMIT = 200
BATCH_SIZE = 5


def generate_coverage(
    output_path: Path = COVERAGE_PATH,
    universities_path: Path = UNIVERSITIES_PATH,
    applications_path: Path = APPLICATIONS_PATH,
    programs_path: Path = PROGRAMS_PATH,
    policies_path: Path = WINDOW_POLICIES_PATH,
    predictions_path: Path = PREDICTIONS_PATH,
    global_rankings_path: Path = GLOBAL_RANKINGS_PATH,
) -> dict:
    university_payload = read_json(universities_path)
    universities = university_payload["universities"]
    applications = read_json(applications_path)["applications"]
    programs = read_json(programs_path)["programs"]
    policies = read_json(policies_path)["policies"]
    predictions = read_json(predictions_path)["predictions"]
    global_rankings = read_json(global_rankings_path, {"rankings": {}}).get(
        "rankings", {}
    )

    top = sorted(
        (
            item
            for item in universities
            if item.get("qsPosition") is not None and item["qsPosition"] <= TOP_LIMIT
        ),
        key=lambda item: item["qsPosition"],
    )
    policies_by_university = {item["universityId"]: item for item in policies}
    program_counts: dict[str, int] = {}
    for program in programs:
        program_counts[program["universityId"]] = (
            program_counts.get(program["universityId"], 0) + 1
        )
    window_counts: dict[str, int] = {}
    for window in applications:
        window_counts[window["universityId"]] = (
            window_counts.get(window["universityId"], 0) + 1
        )
    prediction_counts: dict[str, int] = {}
    for prediction in predictions:
        prediction_counts[prediction["universityId"]] = (
            prediction_counts.get(prediction["universityId"], 0) + 1
        )

    rows = []
    for university in top:
        university_id = university["id"]
        policy = policies_by_university.get(university_id)
        programme_count = program_counts.get(university_id, 0)
        window_count = window_counts.get(university_id, 0)
        prediction_count = prediction_counts.get(university_id, 0)
        rows.append(
            {
                "universityId": university_id,
                "qsPosition": university["qsPosition"],
                "qsRank": university["qsRank"],
                "rankDisplay": university["rankDisplay"],
                "school": university["school"],
                "country": university["country"],
                "batch": ((university["qsPosition"] - 1) // BATCH_SIZE) + 1,
                "entryStatus": university["admissionsDiscovery"],
                "entryLocated": bool(university.get("admissionsUrl")),
                "policyStatus": "verified" if policy else "pending",
                "policyModel": policy.get("model") if policy else None,
                "mastersAvailability": (
                    policy.get("mastersAvailability", "unclear")
                    if policy
                    else "unverified"
                ),
                "cycleGuidance": policy.get("cycleGuidance") if policy else None,
                "programmeCount": programme_count,
                "windowCount": window_count,
                "predictionCount": prediction_count,
                "nextAction": next_action(
                    bool(university.get("admissionsUrl")),
                    policy,
                    programme_count,
                    window_count,
                ),
            }
        )

    batches = []
    for batch_number in range(1, (TOP_LIMIT // BATCH_SIZE) + 1):
        batch_rows = [row for row in rows if row["batch"] == batch_number]
        batches.append(
            {
                "batch": batch_number,
                "positions": [
                    batch_rows[0]["qsPosition"],
                    batch_rows[-1]["qsPosition"],
                ],
                "universities": len(batch_rows),
                "entriesLocated": sum(row["entryLocated"] for row in batch_rows),
                "policiesVerified": sum(
                    row["policyStatus"] == "verified" for row in batch_rows
                ),
                "universitiesWithPrograms": sum(
                    row["programmeCount"] > 0 for row in batch_rows
                ),
                "universitiesWithWindows": sum(
                    row["windowCount"] > 0 for row in batch_rows
                ),
                "predictedWindows": sum(row["predictionCount"] for row in batch_rows),
            }
        )

    summary = _summarise_rows(rows)
    university_by_id = {item["id"]: item for item in universities}
    ranking_ids = {
        "qs": {item["id"] for item in top},
        "the": {
            item["universityId"]
            for item in global_rankings.get("the", {}).get("rows", [])
        },
        "arwu": {
            item["universityId"]
            for item in global_rankings.get("arwu", {}).get("rows", [])
        },
    }
    ranking_ids["union"] = set().union(*ranking_ids.values())
    ranking_coverage = {
        ranking_id: _summarise_university_ids(
            university_ids,
            university_by_id=university_by_id,
            policies_by_university=policies_by_university,
            program_counts=program_counts,
            window_counts=window_counts,
            prediction_counts=prediction_counts,
        )
        for ranking_id, university_ids in ranking_ids.items()
    }
    payload = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "rankingScope": (
                "QS, THE, and ARWU top-200 views plus their deduplicated "
                "canonical-university union"
            ),
            "batchSize": BATCH_SIZE,
            "definition": (
                "Entry, policy, programme, and exact-window coverage are counted "
                "separately. Predictions never count as verified deadlines."
            ),
        },
        "summary": summary,
        "rankingCoverage": ranking_coverage,
        "batches": batches,
        "universities": rows,
    }
    write_json(output_path, payload)
    return payload


def _summarise_university_ids(
    university_ids: set[str],
    *,
    university_by_id: dict[str, dict],
    policies_by_university: dict[str, dict],
    program_counts: dict[str, int],
    window_counts: dict[str, int],
    prediction_counts: dict[str, int],
) -> dict:
    rows = []
    for university_id in sorted(university_ids):
        university = university_by_id.get(university_id, {})
        policy = policies_by_university.get(university_id)
        programme_count = program_counts.get(university_id, 0)
        window_count = window_counts.get(university_id, 0)
        prediction_count = prediction_counts.get(university_id, 0)
        rows.append(
            {
                "entryLocated": bool(university.get("admissionsUrl")),
                "entryStatus": university.get("admissionsDiscovery"),
                "policyStatus": "verified" if policy else "pending",
                "cycleGuidance": policy.get("cycleGuidance") if policy else None,
                "mastersAvailability": (
                    policy.get("mastersAvailability", "unclear")
                    if policy
                    else "unverified"
                ),
                "programmeCount": programme_count,
                "windowCount": window_count,
                "predictionCount": prediction_count,
                "nextAction": next_action(
                    bool(university.get("admissionsUrl")),
                    policy,
                    programme_count,
                    window_count,
                ),
            }
        )
    return _summarise_rows(rows)


def _summarise_rows(rows: list[dict]) -> dict:
    return {
        "targetUniversities": len(rows),
        "entriesLocated": sum(row["entryLocated"] for row in rows),
        "curatedEntries": sum(row["entryStatus"] == "curated" for row in rows),
        "policiesVerified": sum(row["policyStatus"] == "verified" for row in rows),
        "cycleGuidanceAvailable": sum(bool(row["cycleGuidance"]) for row in rows),
        "broadMastersAvailability": sum(
            row["mastersAvailability"] == "broad" for row in rows
        ),
        "limitedMastersAvailability": sum(
            row["mastersAvailability"] == "limited" for row in rows
        ),
        "universitiesWithPrograms": sum(row["programmeCount"] > 0 for row in rows),
        "universitiesWithWindows": sum(row["windowCount"] > 0 for row in rows),
        "verifiedWindows": sum(row["windowCount"] for row in rows),
        "universitiesWithPredictions": sum(row["predictionCount"] > 0 for row in rows),
        "predictedWindows": sum(row["predictionCount"] for row in rows),
        "nextActions": {
            action: sum(row["nextAction"] == action for row in rows)
            for action in (
                "locate-official-entry",
                "verify-window-policy",
                "select-target-programmes",
                "verify-exact-windows",
                "monitor-and-refresh",
            )
        },
    }


def next_action(
    entry_located: bool,
    policy: dict | None,
    programme_count: int,
    window_count: int,
) -> str:
    if not entry_located:
        return "locate-official-entry"
    if not policy:
        return "verify-window-policy"
    if programme_count == 0:
        return "select-target-programmes"
    if window_count == 0:
        return "verify-exact-windows"
    return "monitor-and-refresh"
