from copy import deepcopy

from gradwindow.reviewed_deadlines import validate_reviewed_deadlines


def valid_record():
    return {
        "id": "sample-2027",
        "universityId": "sample",
        "programmeId": "sample-ms",
        "intake": "2027-2028 academic year",
        "round": "Main deadline",
        "applicantCategories": ["all"],
        "closesAt": "2026-12-01",
        "sourceUrl": "https://sample.edu/ms",
        "verifiedAt": "2026-01-01",
        "reviewedBy": "reviewer",
        "evidence": [
            {
                "sourceUrl": "https://sample.edu/ms",
                "excerpt": "Master of Science. Deadline: December 1, 2026.",
            }
        ],
    }


def errors(record):
    return validate_reviewed_deadlines(
        {"deadlines": [record]},
        [{"id": "sample", "officialDomains": ["sample.edu"]}],
        [{"id": "sample-ms", "universityId": "sample"}],
        [{"id": "all"}],
    )


def test_reviewed_deadline_does_not_require_or_invent_opening():
    assert errors(valid_record()) == []
    record = valid_record()
    record["opensAt"] = "2026-09-01"
    assert errors(record)


def test_deadline_requires_exact_date_review_and_official_evidence():
    for field, value in [
        ("closesAt", "December 2026"),
        ("reviewedBy", " "),
        ("sourceUrl", "https://third-party.example/ms"),
        ("programmeId", "unknown"),
        ("applicantCategories", ["unknown"]),
        ("dataStatus", "official"),
        ("evidence", []),
    ]:
        record = deepcopy(valid_record())
        record[field] = value
        assert errors(record), field


def test_unknown_opening_is_not_an_application_window():
    import pytest
    from pydantic import ValidationError

    from gradwindow.models import ApplicationWindow

    with pytest.raises(ValidationError):
        ApplicationWindow.model_validate(valid_record())


def test_approval_is_explicit_and_invalid_drafts_do_not_change_public_data(
    tmp_path, monkeypatch
):
    import pytest

    import gradwindow.reviewed_deadlines as module
    from gradwindow.io import read_json, write_json

    datasets = {
        "UNIVERSITIES_PATH": {
            "universities": [{"id": "sample", "officialDomains": ["sample.edu"]}]
        },
        "PROGRAMS_PATH": {"programs": [{"id": "sample-ms", "universityId": "sample"}]},
        "APPLICANT_CATEGORIES_PATH": {"categories": [{"id": "all"}]},
        "REVIEWED_DEADLINES_PATH": {"deadlines": []},
    }
    for name, payload in datasets.items():
        path = tmp_path / f"{name}.json"
        write_json(path, payload)
        monkeypatch.setattr(module, name, path)
    draft = tmp_path / "draft.json"
    write_json(draft, valid_record())
    record = module.approve_deadline_file(draft, "explicit-reviewer")
    assert record["reviewedBy"] == "explicit-reviewer"
    assert record["opensAt"] is None
    assert record["dataStatus"] == "deadline-only"
    before = read_json(module.REVIEWED_DEADLINES_PATH)
    with pytest.raises(ValueError, match="already exists"):
        module.approve_deadline_file(draft, "reviewer")
    invalid = valid_record()
    invalid["id"] = "another-id"
    invalid["sourceUrl"] = "https://other.example/programme"
    write_json(draft, invalid)
    with pytest.raises(ValueError):
        module.approve_deadline_file(draft, "reviewer")
    assert read_json(module.REVIEWED_DEADLINES_PATH) == before
