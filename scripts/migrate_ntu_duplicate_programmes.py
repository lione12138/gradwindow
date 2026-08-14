from __future__ import annotations

from pathlib import Path

from gradwindow.io import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
UNIVERSITY_ID = "nanyang-technological-university-singapore-ntu-singapore"
PROGRAMME_IDS = {
    "ntu-integrated-circuits-microelectronics-msc": (
        "ntu-integrated-circuits-and-microelectronics-msc"
    ),
    "ntu-signal-processing-machine-learning-msc": (
        "ntu-signal-processing-and-machine-learning-msc"
    ),
}
APPLICATION_IDS = {
    f"{duplicate}-2027-semester-2": f"{canonical}-2027-semester-2"
    for duplicate, canonical in PROGRAMME_IDS.items()
}


def _write(path: str, payload: dict) -> None:
    write_json(ROOT / path, payload)


def _merge_public_programmes() -> int:
    path = ROOT / "data/programs.json"
    payload = read_json(path)
    programmes = payload.get("programs", [])
    ids = {item.get("id") for item in programmes}
    for duplicate, canonical in PROGRAMME_IDS.items():
        if duplicate in ids and canonical not in ids:
            raise ValueError(f"Cannot remove {duplicate}; {canonical} is missing")
    before = len(programmes)
    payload["programs"] = [
        item for item in programmes if item.get("id") not in PROGRAMME_IDS
    ]
    _write("data/programs.json", payload)
    return before - len(payload["programs"])


def _merge_public_applications() -> int:
    path = ROOT / "data/applications.json"
    payload = read_json(path)
    applications = payload.get("applications", [])
    by_id = {item.get("id"): item for item in applications}
    comparison_fields = (
        "universityId",
        "intake",
        "round",
        "applicantCategories",
        "opensAt",
        "closesAt",
        "applicationUrl",
        "sourceUrl",
    )
    for duplicate_id, canonical_id in APPLICATION_IDS.items():
        duplicate = by_id.get(duplicate_id)
        canonical = by_id.get(canonical_id)
        if duplicate is None:
            continue
        if canonical is None:
            raise ValueError(f"Cannot remove {duplicate_id}; {canonical_id} is missing")
        if any(duplicate.get(key) != canonical.get(key) for key in comparison_fields):
            raise ValueError(f"Duplicate application windows differ: {duplicate_id}")
        canonical["verifiedAt"] = max(
            str(canonical.get("verifiedAt") or ""),
            str(duplicate.get("verifiedAt") or ""),
        )
    before = len(applications)
    payload["applications"] = [
        item for item in applications if item.get("id") not in APPLICATION_IDS
    ]
    _write("data/applications.json", payload)
    return before - len(payload["applications"])


def _merge_translations() -> int:
    payload = read_json(ROOT / "data/programme-translations.json")
    translations = payload.get("translations", {})
    removed = 0
    for duplicate, canonical in PROGRAMME_IDS.items():
        duplicate_translation = translations.get(duplicate)
        canonical_translation = translations.get(canonical)
        if duplicate_translation is None:
            continue
        if canonical_translation is None:
            translations[canonical] = duplicate_translation
        else:
            aliases = list(canonical_translation.get("aliasesZh") or [])
            for alias in duplicate_translation.get("aliasesZh") or []:
                if alias not in aliases:
                    aliases.append(alias)
            canonical_translation["aliasesZh"] = aliases
        del translations[duplicate]
        removed += 1
    _write("data/programme-translations.json", payload)
    return removed


def _remove_duplicate_application_state() -> int:
    payload = read_json(ROOT / "data/ops/application-source-state.json")
    applications = payload.get("applications", {})
    removed = 0
    for duplicate_id, canonical_id in APPLICATION_IDS.items():
        duplicate = applications.pop(duplicate_id, None)
        if duplicate is None:
            continue
        canonical = applications.get(canonical_id)
        if canonical is None or str(duplicate.get("checkedAt") or "") > str(
            canonical.get("checkedAt") or ""
        ):
            duplicate["recordId"] = canonical_id
            applications[canonical_id] = duplicate
        removed += 1
    _write("data/ops/application-source-state.json", payload)
    return removed


def _remove_duplicate_evidence() -> int:
    relative_path = (
        "data/evidence/nanyang-technological-university-singapore-ntu-singapore.json"
    )
    payload = read_json(ROOT / relative_path)
    snapshots = payload.get("snapshots", {})
    removed = 0
    for duplicate_id, canonical_id in APPLICATION_IDS.items():
        duplicate = snapshots.pop(duplicate_id, None)
        if duplicate is None:
            continue
        canonical = snapshots.get(canonical_id)
        if canonical is None or str(duplicate.get("capturedAt") or "") > str(
            canonical.get("capturedAt") or ""
        ):
            duplicate["recordId"] = canonical_id
            snapshots[canonical_id] = duplicate
        removed += 1
    _write(relative_path, payload)
    return removed


def _remove_duplicate_candidates() -> int:
    relative_path = "data/ops/programme-candidates.json"
    payload = read_json(ROOT / relative_path)
    items = payload.get("items", [])
    before = len(items)
    payload["items"] = [
        item
        for item in items
        if item.get("programme", {}).get("id") not in PROGRAMME_IDS
    ]
    _write(relative_path, payload)
    return before - len(payload["items"])


def _canonicalise_catalog_state() -> int:
    relative_path = "data/ops/programme-catalog-state.json"
    payload = read_json(ROOT / relative_path)
    university = payload.get("universities", {}).get(UNIVERSITY_ID, {})
    programmes = university.get("programmes", {})
    public_programmes = {
        item["id"]: item
        for item in read_json(ROOT / "data/programs.json").get("programs", [])
        if item.get("universityId") == UNIVERSITY_ID
    }
    changed = 0
    for duplicate, canonical in PROGRAMME_IDS.items():
        snapshot = programmes.pop(duplicate, None)
        if snapshot is None:
            continue
        snapshot["name"] = public_programmes[canonical]["name"]
        programmes[canonical] = snapshot
        changed += 1
    windows = university.get("windows", {})
    for window_id in list(windows):
        duplicate = next(
            (item for item in PROGRAMME_IDS if window_id.startswith(f"{item}::")),
            None,
        )
        if duplicate is None:
            continue
        canonical = PROGRAMME_IDS[duplicate]
        replacement_id = canonical + window_id[len(duplicate) :]
        snapshot = windows.pop(window_id)
        snapshot["programmeId"] = canonical
        windows[replacement_id] = snapshot
        changed += 1
    _write(relative_path, payload)
    return changed


def _remove_duplicate_review_items() -> int:
    relative_path = "data/ops/review-queue.json"
    payload = read_json(ROOT / relative_path)
    items = payload.get("items", [])
    before = len(items)
    payload["items"] = [
        item for item in items if item.get("recordId") not in APPLICATION_IDS
    ]
    _write(relative_path, payload)
    return before - len(payload["items"])


def main() -> None:
    results = {
        "programmes": _merge_public_programmes(),
        "applications": _merge_public_applications(),
        "translations": _merge_translations(),
        "applicationState": _remove_duplicate_application_state(),
        "evidence": _remove_duplicate_evidence(),
        "programmeCandidates": _remove_duplicate_candidates(),
        "catalogState": _canonicalise_catalog_state(),
        "reviewItems": _remove_duplicate_review_items(),
    }
    print(results)


if __name__ == "__main__":
    main()
