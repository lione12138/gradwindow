from __future__ import annotations

import json
from dataclasses import replace

import pytest

from gradwindow.programme_adapters.hku import HKUAdapter, _official_opening

LISTING_PAYLOAD = {
    "data": [
        {
            "Attributes": {
                "hkutgp_name": "Master of Data Science",
                "hkutgp_programmenameabbreviation": "MDASC",
                "rootprogramme.hkutgp_name": {"Value": "master-of-data-science-cds"},
            },
            "FormattedValues": {
                "hkutgp_facultyid": "School of Computing and Data Science"
            },
        },
        {
            "Attributes": {
                "hkutgp_name": "Doctor of Education",
                "rootprogramme.hkutgp_name": {"Value": "doctor-of-education-edu"},
            },
            "FormattedValues": {"hkutgp_facultyid": "Faculty of Education"},
        },
    ],
    "total": 2,
}

DETAIL_HTML = """
<html><body>
  <h1>Master of Data Science</h1>
  <section>
    Programme Highlights: Full-time
    Expected Programme Start Date September 2026
    Application Deadline
    Round 1 (Main): 12:00 noon (GMT +8), December 01, 2025
    Round 2 (Clearing): 12:00 noon (GMT +8), March 31, 2026
    Description Full Time Closed to Applications
  </section>
</body></html>
"""


def test_hku_adapter_extracts_listing_and_deadline_rounds() -> None:
    adapter = HKUAdapter(minimum_expected_programmes=1, detail_workers=1)

    def fetcher(url: str) -> str:
        if "SavedQueryService" in url:
            return json.dumps(LISTING_PAYLOAD)
        assert "master-of-data-science-cds" in url
        return DETAIL_HTML

    catalog = adapter.parse_catalog_from_fetcher(fetcher)

    assert catalog.application_opens_at is None
    assert [item.id for item in catalog.programmes] == ["hku-data-science-master"]
    programme = catalog.programmes[0]
    assert programme.degree_type == "Master"
    assert programme.faculty == "School of Computing and Data Science"
    assert programme.parse_status == "incomplete"
    assert [
        (window.round, window.closes_at, window.opens_at)
        for window in programme.windows
    ] == [
        ("Round 1 (Main)", "2025-12-01", None),
        ("Round 2 (Clearing)", "2026-03-31", None),
    ]
    assert programme.windows[0].intake == "September 2026"


def test_hku_adapter_omits_intake_parenthetical_from_programme_id() -> None:
    payload = {
        "data": [
            {
                "Attributes": {
                    "hkutgp_name": "Master of Science in Advanced Architectural Design (September 2026)",
                    "rootprogramme.hkutgp_name": {
                        "Value": "master-of-science-in-advanced-architectural-design-september-2026-foa"
                    },
                },
                "FormattedValues": {"hkutgp_facultyid": "Faculty of Architecture"},
            }
        ],
        "total": 1,
    }
    adapter = HKUAdapter(minimum_expected_programmes=1, detail_workers=1)

    def fetcher(url: str) -> str:
        if "SavedQueryService" in url:
            return json.dumps(payload)
        return "<html><body>No deadline</body></html>"

    catalog = adapter.parse_catalog_from_fetcher(fetcher)

    assert catalog.programmes[0].id == "hku-advanced-architectural-design-msc"


@pytest.mark.parametrize(
    "text",
    [
        "Application for 2027-28 intake opens on 2 November 2026",
        "For 2027–28 intake: Application opens in 2 November 2026",
        "2 Nov 2026 Application Opens for 2027/28 Intake",
        "The application period for 2027-2028 admission will begin on November 2, 2026",
    ],
)
def test_hku_reads_explicit_cycle_scoped_opening(text):
    assert _official_opening(text, "September 2027") == ("2026-11-02", text)
    assert _official_opening(text, "September 2028") is None


def test_hku_does_not_invent_opening_or_merge_conflicting_announcements():
    first = "Application for 2027-28 intake opens on 2 November 2026."
    assert (
        _official_opening(first.replace("2 November", "November"), "September 2027")
        is None
    )
    assert (
        _official_opening(
            first + first.replace("2 November", "3 November"), "September 2027"
        )
        is None
    )


def test_hku_reconciles_official_opening_and_full_time_applicant_scope():
    adapter = HKUAdapter()
    seed = adapter._programme_from_api_item(LISTING_PAYLOAD["data"][0])
    programme = replace(seed, id="hku-master-of-public-health-mph")
    detail = """
    <div class="tab-pane active">Expected Programme Start Date 2027 September
    Application Deadline Round 1 (Main): April 30, 2027
    Round 2 (Clearing) (for local applicants only): June 30, 2027 Description</div>
    <div class="tab-pane">Expected Programme Start Date September 2027
    Application Deadline Round 1 (Main): May 15, 2027 Description</div>
    """
    parsed = adapter._parse_detail(
        programme, detail, "2 Nov 2026 Application Opens for 2027/28 Intake"
    )
    assert [
        (w.closes_at, w.applicant_categories, w.opens_at, w.opens_at_basis)
        for w in parsed.windows
    ] == [
        ("2027-04-30", ["all"], "2026-11-02", "official"),
        ("2027-06-30", ["hku-local"], "2026-11-02", "official"),
    ]
    assert (
        adapter._parse_detail(
            programme, detail.replace("2027 September", "To be updated")
        ).windows
        == []
    )


def test_hku_preserves_local_and_non_local_deadlines():
    adapter = HKUAdapter()
    seed = adapter._programme_from_api_item(LISTING_PAYLOAD["data"][0])
    detail = "Expected Programme Start Date September 2027 Application Deadline Non-local students: April 30, 2027 Local students: June 30, 2027 Description"
    parsed = adapter._parse_detail(seed, detail)
    assert [w.applicant_categories for w in parsed.windows] == [
        ["hku-non-local"],
        ["hku-local"],
    ]
    assert all(
        w.opens_at is None and w.opens_at_basis == "missing" for w in parsed.windows
    )
