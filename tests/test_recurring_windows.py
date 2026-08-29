from __future__ import annotations

import json
from pathlib import Path

from gradwindow.recurring_windows import generate_recurring_windows


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_generate_recurring_windows_publishes_only_official_recurring_policy(
    tmp_path: Path,
) -> None:
    universities_path = tmp_path / "universities.json"
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    output_path = tmp_path / "recurring-windows.json"

    _write_json(
        universities_path,
        {
            "meta": {"version": 1, "updatedAt": "2026-08-11"},
            "universities": [
                {
                    "id": "tum",
                    "name": "Technical University of Munich",
                    "country": "Germany",
                    "rankings": {"qs": 22},
                    "officialDomains": ["tum.de"],
                }
            ],
        },
    )
    _write_json(
        programs_path,
        {
            "meta": {"version": 1, "updatedAt": "2026-08-11"},
            "programs": [
                {
                    "id": "tum-informatics-msc",
                    "universityId": "tum",
                    "name": "Informatics",
                    "degree": "MSc",
                    "field": "Computer Science",
                    "studyMode": "full-time",
                    "applicationUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
                    "active": True,
                }
            ],
        },
    )
    _write_json(
        applications_path,
        {"meta": {"version": 1, "updatedAt": "2026-08-11"}, "applications": []},
    )
    _write_json(
        candidates_path,
        {
            "meta": {"version": 1, "updatedAt": "2026-08-11"},
            "items": [
                {
                    "id": "known-programme-guidance:tum-informatics-msc",
                    "type": "known-programme-recurring-policy",
                    "status": "published",
                    "universityId": "tum",
                    "programme": {
                        "id": "tum-informatics-msc",
                        "name": "Informatics",
                        "applicationUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
                    },
                    "sourceUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
                    "detectedAt": "2026-08-11T01:00:00Z",
                    "evidenceExcerpt": "Summer semester: 01.10. - 30.11.",
                    "windows": [
                        {
                            "intake": "2027 spring",
                            "round": "main",
                            "applicantCategories": ["all"],
                            "opensAt": "2026-10-01",
                            "closesAt": "2026-11-30",
                            "deadlineSemantics": "before",
                            "opensAtBasis": "official-recurring-policy",
                            "sourceUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
                        },
                        {
                            "intake": "2027 fall",
                            "round": "main",
                            "applicantCategories": ["all"],
                            "opensAt": "2027-04-01",
                            "closesAt": "2027-05-31",
                            "opensAtBasis": "inferred",
                            "sourceUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
                        },
                    ],
                }
            ],
        },
    )
    _write_json(
        state_path,
        {
            "meta": {"version": 1, "updatedAt": "2026-08-11"},
            "universities": {
                "tum": {"status": "ok", "checkedAt": "2026-08-11T02:30:00Z"}
            },
        },
    )

    result = generate_recurring_windows(
        universities_path=universities_path,
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        state_path=state_path,
        output_path=output_path,
        today="2026-08-11",
    )

    assert result == {
        "recurringPolicyWindows": 1,
        "universities": 1,
        "suppressedByOfficialRecords": 0,
    }
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["meta"]["dataStatus"] == "official-recurring-policy"
    assert payload["recurringWindows"] == [
        {
            "id": "recurring-tum-informatics-msc-2027-spring-main-all",
            "universityId": "tum",
            "scopeType": "programme",
            "scopeId": "tum-informatics-msc",
            "intake": "2027 spring",
            "intakeDetails": {
                "label": "2027 spring",
                "cycleYear": 2027,
                "academicYearEnd": None,
                "term": "spring",
                "startMonth": 1,
            },
            "entryPattern": "fixed",
            "startDatePrecision": "term",
            "round": "main",
            "applicantCategories": ["all"],
            "opensAt": "2026-10-01",
            "closesAt": "2026-11-30",
            "deadlineSemantics": "before",
            "applicationUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
            "sourceUrl": "https://www.tum.de/studies/degree-programs/detail/informatics-master-of-science-msc",
            "policyCheckedAt": "2026-08-11",
            "dateBasis": "official-recurring-policy",
            "cycleYearBasis": "system-materialized-next-cycle",
            "evidence": "Summer semester: 01.10. - 30.11.",
        }
    ]


def test_generate_recurring_windows_suppresses_an_equivalent_official_record(
    tmp_path: Path,
) -> None:
    universities_path = tmp_path / "universities.json"
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    output_path = tmp_path / "recurring-windows.json"

    _write_json(
        universities_path,
        {
            "universities": [
                {
                    "id": "tum",
                    "name": "Technical University of Munich",
                    "country": "Germany",
                    "rankings": {"qs": 22},
                    "officialDomains": ["tum.de"],
                }
            ]
        },
    )
    _write_json(
        programs_path,
        {
            "programs": [
                {
                    "id": "tum-informatics-msc",
                    "universityId": "tum",
                    "name": "Informatics",
                    "degree": "MSc",
                    "field": "Computer Science",
                    "studyMode": "full-time",
                    "applicationUrl": "https://www.tum.de/program",
                    "active": True,
                }
            ]
        },
    )
    _write_json(
        applications_path,
        {
            "applications": [
                {
                    "id": "official-tum-informatics",
                    "universityId": "tum",
                    "scopeType": "programme",
                    "scopeId": "tum-informatics-msc",
                    "intake": "2027 spring",
                    "intakeDetails": {
                        "label": "2027 spring",
                        "cycleYear": 2027,
                        "academicYearEnd": None,
                        "term": "spring",
                        "startMonth": 1,
                    },
                    "round": "main",
                    "applicantCategories": ["all"],
                    "opensAt": "2026-10-01",
                    "closesAt": "2026-11-30",
                    "applicationUrl": "https://www.tum.de/apply",
                    "sourceUrl": "https://www.tum.de/program",
                    "verifiedAt": "2026-08-11",
                }
            ]
        },
    )
    _write_json(
        candidates_path,
        {
            "items": [
                {
                    "id": "known-programme-guidance:tum-informatics-msc",
                    "type": "known-programme-recurring-policy",
                    "status": "published",
                    "universityId": "tum",
                    "programme": {
                        "id": "tum-informatics-msc",
                        "name": "Informatics",
                        "applicationUrl": "https://www.tum.de/program",
                    },
                    "sourceUrl": "https://www.tum.de/program",
                    "detectedAt": "2026-08-11T01:00:00Z",
                    "windows": [
                        {
                            "intake": "2027 spring",
                            "round": "main",
                            "applicantCategories": ["all"],
                            "opensAt": "2026-10-01",
                            "closesAt": "2026-11-30",
                            "opensAtBasis": "official-recurring-policy",
                            "sourceUrl": "https://www.tum.de/program",
                        }
                    ],
                }
            ]
        },
    )
    _write_json(
        state_path,
        {"universities": {"tum": {"checkedAt": "2026-08-11T02:30:00Z"}}},
    )

    result = generate_recurring_windows(
        universities_path=universities_path,
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        state_path=state_path,
        output_path=output_path,
        today="2026-08-11",
    )

    assert result["recurringPolicyWindows"] == 0
    assert result["suppressedByOfficialRecords"] == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["recurringWindows"] == []
