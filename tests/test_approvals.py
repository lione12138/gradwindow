from __future__ import annotations

import json

import pytest

from gradwindow.approvals import (
    approve_official_adapter_window_candidates,
    approve_programme_candidates,
    approve_window,
)
from gradwindow.paths import APPLICATIONS_PATH, PROGRAMS_PATH


def test_approve_window_promotes_valid_candidate(tmp_path) -> None:
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "candidates.json"
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidate_record = {
        "id": "eth-example-2027",
        "universityId": "eth-zurich-swiss-federal-institute-of-technology",
        "scopeType": "institution",
        "scopeId": "eth-zurich-swiss-federal-institute-of-technology",
        "intake": "2027 Fall",
        "round": "",
        "applicantCategories": ["all"],
        "opensAt": "2026-09-01",
        "closesAt": "2026-12-01",
        "applicationUrl": "https://ethz.ch/en/studies/master/application.html",
        "sourceUrl": "https://ethz.ch/en/studies/master/application/dates.html",
        "verifiedAt": "2026-06-14",
        "evidence": "Fixture with explicit dates for approval workflow testing.",
    }
    candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {
                        "id": "candidate-1",
                        "status": "pending",
                        "record": candidate_record,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    approved = approve_window(
        "candidate-1",
        "test-reviewer",
        candidates_path,
        applications_path,
    )
    assert approved["id"] == "eth-example-2027"
    applications = json.loads(applications_path.read_text(encoding="utf-8"))
    assert any(
        item["id"] == "eth-example-2027" for item in applications["applications"]
    )
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    assert candidates["items"][0]["status"] == "approved"
    assert candidates["items"][0]["reviewedBy"] == "test-reviewer"


def test_approve_window_rejects_unknown_candidate(tmp_path) -> None:
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text('{"items": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown candidate"):
        approve_window(
            "missing",
            "test-reviewer",
            candidates_path,
            APPLICATIONS_PATH,
        )


def test_parser_candidate_gets_fresh_review_evidence(tmp_path) -> None:
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "candidates.json"
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    applications = json.loads(applications_path.read_text(encoding="utf-8"))
    record = next(
        item
        for item in applications["applications"]
        if item["id"] == "eth-autumn-2026-swiss-bachelors"
    )
    proposed = {**record, "closesAt": "2026-05-01"}
    candidates_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "parser-candidate",
                        "type": "parser-date-change",
                        "status": "pending",
                        "record": proposed,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    approved = approve_window(
        "parser-candidate",
        "test-reviewer",
        candidates_path,
        applications_path,
    )
    assert "test-reviewer reviewed the official source" in approved["evidence"]
    assert "2026-04-01 to 2026-05-01" in approved["evidence"]


def test_approve_programme_candidates_promotes_parsed_windows(tmp_path) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    programs_path.write_text(
        PROGRAMS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidate = {
        "id": "new-programme:imperial-example-msc",
        "type": "new-programme",
        "status": "pending",
        "universityId": "imperial-college-london",
        "programme": {
            "id": "imperial-example-msc",
            "universityId": "imperial-college-london",
            "name": "MSc Example",
            "degreeType": "MSc",
            "faculty": "Department A | Department A",
            "applicationUrl": "https://myimperial.powerappsportals.com/",
            "sourceUrl": (
                "https://www.imperial.ac.uk/study/courses/"
                "postgraduate-taught/2026/example/"
            ),
        },
        "windows": [
            {
                "intake": "September 2026",
                "round": "Round 2",
                "applicantCategories": ["all"],
                "opensAt": "2025-09-29",
                "opensAtBasis": "official",
                "closesAt": "2026-01-07",
                "deadlineSemantics": "before",
                "scopeType": "institution",
                "scopeId": "imperial-college-london",
            }
        ],
        "parseStatus": "parsed",
    }
    candidates_path.write_text(
        json.dumps({"meta": {}, "items": [candidate]}),
        encoding="utf-8",
    )

    report = approve_programme_candidates(
        university_id="imperial-college-london",
        reviewer="test-reviewer",
        candidates_path=candidates_path,
        programs_path=programs_path,
        applications_path=applications_path,
    )

    assert report["promotedProgrammes"] == 1
    assert report["promotedWindows"] == 1
    programs = json.loads(programs_path.read_text(encoding="utf-8"))["programs"]
    programme = next(item for item in programs if item["id"] == "imperial-example-msc")
    assert programme["faculty"] == "Department A"
    applications = json.loads(applications_path.read_text(encoding="utf-8"))[
        "applications"
    ]
    window = next(
        item
        for item in applications
        if item["id"] == "imperial-example-msc-2026-round-2"
    )
    assert window["scopeType"] == "institution"
    assert window["scopeId"] == "imperial-college-london"
    assert window["intakeDetails"]["cycleYear"] == 2026
    assert window["deadlineSemantics"] == "before"
    assert "requiring submission before 2026-01-07" in window["evidence"]
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert candidates[0]["status"] == "approved"


def test_approve_programme_candidates_rejects_inferred_opening(tmp_path) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    programs_path.write_text(
        PROGRAMS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidates_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "new-programme:inferred-example",
                        "type": "new-programme",
                        "status": "pending",
                        "universityId": "imperial-college-london",
                        "programme": {
                            "id": "inferred-example",
                            "universityId": "imperial-college-london",
                            "name": "MSc Inferred Example",
                            "degreeType": "MSc",
                            "faculty": "",
                            "applicationUrl": "https://www.imperial.ac.uk/study/",
                            "sourceUrl": "https://www.imperial.ac.uk/study/",
                        },
                        "windows": [
                            {
                                "intake": "September 2027",
                                "round": "Main",
                                "applicantCategories": ["all"],
                                "opensAt": "2026-10-01",
                                "opensAtBasis": "inferred-cycle-default",
                                "closesAt": "2027-01-01",
                            }
                        ],
                        "parseStatus": "parsed",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = approve_programme_candidates(
        university_id="imperial-college-london",
        reviewer="test-reviewer",
        candidates_path=candidates_path,
        programs_path=programs_path,
        applications_path=applications_path,
    )

    assert report["promotedProgrammes"] == 0
    assert report["promotedWindows"] == 0
    assert report["remainingPending"] == 1


def test_approve_programme_candidates_can_publish_catalogue_only_records(
    tmp_path,
) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    programs_path.write_text(
        PROGRAMS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidate = {
        "id": "new-programme:catalogue-only-example",
        "type": "new-programme",
        "status": "pending",
        "universityId": "imperial-college-london",
        "programme": {
            "id": "catalogue-only-example",
            "universityId": "imperial-college-london",
            "name": "MSc Catalogue Only Example",
            "degreeType": "MSc",
            "faculty": "Department A",
            "applicationUrl": "https://www.imperial.ac.uk/study/",
            "sourceUrl": "https://www.imperial.ac.uk/study/courses/",
        },
        "windows": [],
        "parseStatus": "no-deadline",
    }
    candidates_path.write_text(
        json.dumps({"meta": {}, "items": [candidate]}), encoding="utf-8"
    )

    report = approve_programme_candidates(
        university_id="imperial-college-london",
        reviewer="test-reviewer",
        parsed_only=False,
        candidates_path=candidates_path,
        programs_path=programs_path,
        applications_path=applications_path,
    )

    assert report == {
        "promotedProgrammes": 1,
        "promotedWindows": 0,
        "remainingPending": 0,
    }
    programs = json.loads(programs_path.read_text(encoding="utf-8"))["programs"]
    assert any(item["id"] == "catalogue-only-example" for item in programs)
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert candidates[0]["status"] == "approved"


def test_approve_programme_candidates_persists_approval_for_existing_programme(
    tmp_path,
) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    programs_payload = json.loads(PROGRAMS_PATH.read_text(encoding="utf-8"))
    existing_programme = programs_payload["programs"][0]
    programs_path.write_text(json.dumps(programs_payload), encoding="utf-8")
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {
                        "id": f"new-programme:{existing_programme['id']}",
                        "type": "new-programme",
                        "status": "pending",
                        "universityId": existing_programme["universityId"],
                        "programme": existing_programme,
                        "windows": [],
                        "parseStatus": "no-deadline",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = approve_programme_candidates(
        university_id=existing_programme["universityId"],
        reviewer="automated-policy",
        parsed_only=False,
        candidates_path=candidates_path,
        programs_path=programs_path,
        applications_path=applications_path,
    )

    assert report == {
        "promotedProgrammes": 0,
        "promotedWindows": 0,
        "remainingPending": 0,
    }
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert candidates[0]["status"] == "approved"
    assert candidates[0]["reviewedBy"] == "automated-policy"


def test_approve_window_rejects_non_official_opening_basis(tmp_path) -> None:
    candidates_path = tmp_path / "window-candidates.json"
    candidates_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "adapter-window:inferred",
                        "type": "adapter-new-window",
                        "status": "pending",
                        "openingBasis": "inferred-cycle-default",
                        "record": {},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="official opening date"):
        approve_window(
            "adapter-window:inferred",
            "test-reviewer",
            candidates_path,
            APPLICATIONS_PATH,
        )


def test_batch_approval_only_promotes_official_adapter_windows(tmp_path) -> None:
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "window-candidates.json"
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    base_record = {
        "universityId": "eth-zurich-swiss-federal-institute-of-technology",
        "scopeType": "institution",
        "scopeId": "eth-zurich-swiss-federal-institute-of-technology",
        "intake": "2027 Fall",
        "round": "Main",
        "applicantCategories": ["all"],
        "opensAt": "2026-09-01",
        "closesAt": "2026-12-01",
        "applicationUrl": "https://ethz.ch/en/studies/master/application.html",
        "sourceUrl": "https://ethz.ch/en/studies/master/application/dates.html",
        "verifiedAt": "2026-07-01",
        "evidence": "Official exact dates used by the batch approval test.",
    }
    candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {
                        "id": "official-adapter-window",
                        "type": "adapter-new-window",
                        "status": "pending",
                        "openingBasis": "official",
                        "record": {**base_record, "id": "batch-official-window"},
                    },
                    {
                        "id": "inferred-adapter-window",
                        "type": "adapter-new-window",
                        "status": "pending",
                        "openingBasis": "inferred-cycle-default",
                        "record": {**base_record, "id": "batch-inferred-window"},
                    },
                    {
                        "id": "parser-window",
                        "type": "parser-date-change",
                        "status": "pending",
                        "openingBasis": "official",
                        "record": {**base_record, "id": "batch-parser-window"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    report = approve_official_adapter_window_candidates(
        reviewer="automated-policy",
        university_ids={"eth-zurich-swiss-federal-institute-of-technology"},
        candidates_path=candidates_path,
        applications_path=applications_path,
    )

    assert report == {"promotedWindows": 1, "remainingPending": 1}
    applications = json.loads(applications_path.read_text(encoding="utf-8"))[
        "applications"
    ]
    assert any(item["id"] == "batch-official-window" for item in applications)
    assert not any(item["id"] == "batch-inferred-window" for item in applications)
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert candidates[0]["status"] == "approved"
    assert candidates[0]["reviewedBy"] == "automated-policy"
    assert candidates[1]["status"] == "pending"
    assert candidates[2]["status"] == "pending"


def test_batch_approval_resolves_identical_semantic_candidates_once(tmp_path) -> None:
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "window-candidates.json"
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    base_record = {
        "universityId": "eth-zurich-swiss-federal-institute-of-technology",
        "scopeType": "institution",
        "scopeId": "eth-zurich-swiss-federal-institute-of-technology",
        "intake": "Fall 2031",
        "round": "Shared main round",
        "applicantCategories": ["all"],
        "opensAt": "2030-09-01",
        "closesAt": "2030-12-01",
        "applicationUrl": "https://ethz.ch/en/studies/master/application.html",
        "sourceUrl": "https://ethz.ch/en/studies/master/application/dates.html",
        "verifiedAt": "2026-08-27",
        "evidence": "The same official institutional window was observed twice.",
    }
    candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {
                        "id": f"candidate-{suffix}",
                        "type": "adapter-new-window",
                        "status": "pending",
                        "openingBasis": "official",
                        "record": {**base_record, "id": f"duplicate-window-{suffix}"},
                    }
                    for suffix in ("a", "b")
                ],
            }
        ),
        encoding="utf-8",
    )

    report = approve_official_adapter_window_candidates(
        reviewer="automated-policy",
        university_ids={"eth-zurich-swiss-federal-institute-of-technology"},
        candidates_path=candidates_path,
        applications_path=applications_path,
    )

    assert report == {"promotedWindows": 1, "remainingPending": 0}
    applications = json.loads(applications_path.read_text(encoding="utf-8"))[
        "applications"
    ]
    assert sum(item["id"].startswith("duplicate-window-") for item in applications) == 1
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert all(item["status"] == "approved" for item in candidates)


def test_batch_approval_keeps_conflicting_semantic_candidates_pending(
    tmp_path,
) -> None:
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "window-candidates.json"
    applications_path.write_text(
        APPLICATIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    base_record = {
        "universityId": "eth-zurich-swiss-federal-institute-of-technology",
        "scopeType": "institution",
        "scopeId": "eth-zurich-swiss-federal-institute-of-technology",
        "intake": "Fall 2032",
        "round": "Conflicting main round",
        "applicantCategories": ["all"],
        "opensAt": "2031-09-01",
        "applicationUrl": "https://ethz.ch/en/studies/master/application.html",
        "sourceUrl": "https://ethz.ch/en/studies/master/application/dates.html",
        "verifiedAt": "2026-08-27",
        "evidence": "Two official observations disagree and require review.",
    }
    candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {
                        "id": f"candidate-{suffix}",
                        "type": "adapter-new-window",
                        "status": "pending",
                        "openingBasis": "official",
                        "record": {
                            **base_record,
                            "id": f"conflicting-window-{suffix}",
                            "closesAt": closes_at,
                        },
                    }
                    for suffix, closes_at in (
                        ("a", "2031-12-01"),
                        ("b", "2031-12-15"),
                    )
                ],
            }
        ),
        encoding="utf-8",
    )

    report = approve_official_adapter_window_candidates(
        reviewer="automated-policy",
        university_ids={"eth-zurich-swiss-federal-institute-of-technology"},
        candidates_path=candidates_path,
        applications_path=applications_path,
    )

    assert report == {"promotedWindows": 0, "remainingPending": 2}
    applications = json.loads(applications_path.read_text(encoding="utf-8"))[
        "applications"
    ]
    assert not any(
        item["id"].startswith("conflicting-window-") for item in applications
    )
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert all(item["status"] == "pending" for item in candidates)
    assert all("manual review" in item["reviewNotes"] for item in candidates)


def test_batch_approval_still_promotes_an_explicit_window_change(tmp_path) -> None:
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "window-candidates.json"
    applications = json.loads(APPLICATIONS_PATH.read_text(encoding="utf-8"))
    existing = {
        "id": "change-window",
        "universityId": "eth-zurich-swiss-federal-institute-of-technology",
        "scopeType": "institution",
        "scopeId": "eth-zurich-swiss-federal-institute-of-technology",
        "intake": "Fall 2033",
        "intakeDetails": {
            "label": "Fall 2033",
            "cycleYear": 2033,
            "academicYearEnd": None,
            "term": "fall",
            "startMonth": 9,
        },
        "round": "Change round",
        "applicantCategories": ["all"],
        "opensAt": "2032-09-01",
        "closesAt": "2032-12-01",
        "applicationUrl": "https://ethz.ch/en/studies/master/application.html",
        "sourceUrl": "https://ethz.ch/en/studies/master/application/dates.html",
        "verifiedAt": "2026-08-26",
        "evidence": "Previously verified official window.",
    }
    applications["applications"].append(existing)
    applications_path.write_text(json.dumps(applications), encoding="utf-8")
    candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {
                        "id": "candidate-change",
                        "type": "adapter-window-change",
                        "status": "pending",
                        "openingBasis": "official",
                        "record": {**existing, "closesAt": "2032-12-15"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = approve_official_adapter_window_candidates(
        reviewer="automated-policy",
        university_ids={"eth-zurich-swiss-federal-institute-of-technology"},
        candidates_path=candidates_path,
        applications_path=applications_path,
    )

    assert report == {"promotedWindows": 1, "remainingPending": 0}
    updated = json.loads(applications_path.read_text(encoding="utf-8"))["applications"]
    changed = next(item for item in updated if item["id"] == "change-window")
    assert changed["closesAt"] == "2032-12-15"
