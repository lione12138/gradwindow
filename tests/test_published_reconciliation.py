from __future__ import annotations

from datetime import date

from gradwindow.io import read_json, write_json
from gradwindow.published_reconciliation import reconcile_published


def _window(record_id: str, scope_id: str, **overrides) -> dict:
    item = {
        "id": record_id,
        "universityId": "example-university",
        "scopeType": "programme",
        "scopeId": scope_id,
        "intake": "September 2027",
        "intakeDetails": {
            "label": "September 2027",
            "cycleYear": 2027,
            "academicYearEnd": None,
            "term": "fall",
            "startMonth": 9,
        },
        "round": "Main",
        "applicantCategories": ["all"],
        "opensAt": "2026-10-01",
        "closesAt": "2027-08-01",
        "sourceUrl": f"https://example.edu/{scope_id}",
        "evidence": "Official programme deadline.",
    }
    item.update(overrides)
    return item


def _snapshot(item: dict, **overrides) -> dict:
    snapshot = {
        "programmeId": item["scopeId"],
        "intake": item["intake"],
        "round": item["round"],
        "applicantCategories": item["applicantCategories"],
        "opensAt": item["opensAt"],
        "closesAt": item["closesAt"],
        "sourceUrl": item["sourceUrl"],
        "opensAtBasis": "official",
    }
    snapshot.update(overrides)
    return snapshot


def _write_inputs(tmp_path):
    unchanged = _window("unchanged-window", "unchanged-msc")
    changed = _window("changed-window", "changed-msc")
    missing = _window("missing-window", "missing-msc")
    source_url = _window("source-url-window", "source-url-msc")
    applications_path = tmp_path / "applications.json"
    catalog_state_path = tmp_path / "catalog-state.json"
    adapter_health_path = tmp_path / "adapter-health.json"
    source_state_path = tmp_path / "source-state.json"
    write_json(
        applications_path,
        {"applications": [unchanged, changed, missing, source_url]},
    )
    write_json(
        catalog_state_path,
        {
            "universities": {
                "example-university": {
                    "checkedAt": "2026-08-30T07:00:00+00:00",
                    "windows": {
                        "unchanged-msc::September 2027::Main::all": _snapshot(
                            unchanged
                        ),
                        "changed-msc::September 2027::Main::all": _snapshot(
                            changed, closesAt="2027-07-01"
                        ),
                        "source-url-msc::September 2027::Main::all": _snapshot(
                            source_url,
                            sourceUrl="https://example.edu/programmes/source-url-msc",
                        ),
                    },
                }
            }
        },
    )
    write_json(
        adapter_health_path,
        {"universities": {"example-university": {"healthStatus": "ok"}}},
    )
    write_json(source_state_path, {"applications": {}})
    return {
        "applications_path": applications_path,
        "catalog_state_path": catalog_state_path,
        "adapter_health_path": adapter_health_path,
        "source_state_path": source_state_path,
    }


def test_reconcile_published_dry_run_classifies_changes_without_writing(
    tmp_path,
) -> None:
    paths = _write_inputs(tmp_path)
    candidates_path = tmp_path / "reconciliation-candidates.json"

    result = reconcile_published(
        **paths,
        candidates_path=candidates_path,
        dry_run=True,
        today=date(2026, 8, 30),
    )

    assert result["summary"] == {
        "universities": 1,
        "recordsCompared": 4,
        "unchanged": 1,
        "deadlineChanged": 1,
        "disappeared": 1,
        "sourceUrlOnlyChanged": 1,
        "intakeMismatches": 0,
        "candidates": 3,
    }
    assert {item["action"] for item in result["candidates"]} == {
        "date-change-review",
        "retire-review",
        "safe-source-url-update",
    }
    assert not candidates_path.exists()


def test_reconcile_published_writes_stable_candidates_and_preserves_other_schools(
    tmp_path,
) -> None:
    paths = _write_inputs(tmp_path)
    candidates_path = tmp_path / "reconciliation-candidates.json"
    write_json(
        candidates_path,
        {
            "meta": {},
            "candidates": [
                {
                    "id": "published-reconciliation:other-window:keep",
                    "universityId": "other-university",
                    "recordId": "other-window",
                    "status": "pending",
                }
            ],
        },
    )

    first = reconcile_published(
        **paths,
        candidates_path=candidates_path,
        university_id="example-university",
        today=date(2026, 8, 30),
    )
    second = reconcile_published(
        **paths,
        candidates_path=candidates_path,
        university_id="example-university",
        today=date(2026, 8, 30),
    )
    written = read_json(candidates_path)

    assert [item["id"] for item in first["candidates"]] == [
        item["id"] for item in second["candidates"]
    ]
    assert len(written["candidates"]) == 4
    assert any(
        item["universityId"] == "other-university" for item in written["candidates"]
    )
    changed = next(
        item for item in written["candidates"] if item["recordId"] == "changed-window"
    )
    assert changed["proposedChanges"] == {"closesAt": "2027-07-01"}
    assert changed["status"] == "pending"
