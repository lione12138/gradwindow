from __future__ import annotations

from datetime import date

from gradwindow.published_data_audit import audit_published_data


def _window(**overrides) -> dict:
    item = {
        "id": "example-msc-fall-2027",
        "universityId": "example-university",
        "scopeType": "programme",
        "scopeId": "example-msc",
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
        "closesAt": "2027-12-01",
        "sourceUrl": "https://example.edu/msc",
        "evidence": "Official programme deadline.",
    }
    item.update(overrides)
    return item


def test_audit_quarantines_a_deadline_far_after_the_nominal_intake() -> None:
    payload = audit_published_data([_window()], today=date(2026, 8, 26))

    assert payload["summary"]["suspiciousIntakeWindows"] == 1
    assert payload["quarantinedRecordIds"] == ["example-msc-fall-2027"]
    assert payload["issues"][0]["type"] == "suspicious-intake-window"
    assert payload["issues"][0]["nominalIntakeMonth"] == "2027-09"


def test_audit_allows_an_explicit_flexible_entry_exception() -> None:
    item = _window(evidence="Official rolling admissions with flexible entry dates.")

    payload = audit_published_data([item], today=date(2026, 8, 26))

    assert payload["issues"] == []
    assert payload["quarantinedRecordIds"] == []


def test_audit_reconciles_future_published_records_to_a_healthy_snapshot() -> None:
    published = _window(closesAt="2027-09-01")
    catalog_state = {
        "example-university": {
            "windows": {},
            "lastSuccessfulAt": "2026-08-26T07:00:00+00:00",
        }
    }
    adapter_health = {
        "example-university": {
            "healthStatus": "ok",
            "lastSuccessfulAt": "2026-08-26T07:00:00+00:00",
        }
    }

    payload = audit_published_data(
        [published],
        catalog_state=catalog_state,
        adapter_health=adapter_health,
        today=date(2026, 8, 26),
    )

    assert payload["summary"]["publishedRecordsMissingFromSnapshot"] == 1
    assert payload["issues"][0]["type"] == "published-record-missing-from-snapshot"
    assert payload["issues"][0]["recommendedAction"] == "retire-or-correct-review"


def test_audit_does_not_reconcile_against_an_unavailable_adapter() -> None:
    payload = audit_published_data(
        [_window(closesAt="2027-09-01")],
        catalog_state={"example-university": {"windows": {}}},
        adapter_health={"example-university": {"healthStatus": "needs-maintenance"}},
        today=date(2026, 8, 26),
    )

    assert payload["issues"] == []


def test_audit_detects_a_changed_published_window() -> None:
    published = _window(closesAt="2027-08-01")
    identity = "example-msc::September 2027::Main::all"
    payload = audit_published_data(
        [published],
        catalog_state={
            "example-university": {
                "windows": {
                    identity: {
                        "programmeId": "example-msc",
                        "intake": "September 2027",
                        "opensAt": "2026-10-01",
                        "closesAt": "2027-07-01",
                        "sourceUrl": "https://example.edu/msc",
                        "opensAtBasis": "official",
                    }
                }
            }
        },
        adapter_health={"example-university": {"healthStatus": "ok"}},
        today=date(2026, 8, 26),
    )

    assert payload["summary"]["publishedRecordsChangedFromSnapshot"] == 1
    assert payload["issues"][0]["type"] == "published-record-changed-from-snapshot"
    assert payload["issues"][0]["differences"] == {
        "closesAt": {"published": "2027-08-01", "snapshot": "2027-07-01"}
    }
