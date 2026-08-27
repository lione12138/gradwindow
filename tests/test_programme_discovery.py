from __future__ import annotations

import json
from io import BytesIO

import pytest
from openpyxl import Workbook

from gradwindow import programme_discovery
from gradwindow.http_client import FetchedPage, FetchFailure
from gradwindow.io import partition_json_file
from gradwindow.programme_adapters.base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)
from gradwindow.programme_adapters.cuhk import CUHKAdapter
from gradwindow.programme_discovery import discover_programmes


def test_recurring_policy_rejects_unknown_applicant_categories(tmp_path) -> None:
    class InvalidRecurringAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"

        def parse_catalog(self, _html):
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="Example faculty",
                        department="Example department",
                        source_url="https://example.edu/programmes/example",
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Main",
                                applicant_categories=["invented-category"],
                                opens_at="2026-09-01",
                                closes_at="2027-01-15",
                                opens_at_basis="official-recurring-policy",
                            )
                        ],
                        deadline_text="Official recurring dates.",
                        parse_status="recurring-policy",
                    )
                ],
            )

    programmes = tmp_path / "programs.json"
    applications = tmp_path / "applications.json"
    candidates = tmp_path / "programme-candidates.json"
    state = tmp_path / "programme-catalog-state.json"
    programmes.write_text('{"programs": []}', encoding="utf-8")
    applications.write_text('{"applications": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="invented-category"):
        discover_programmes(
            InvalidRecurringAdapter(),
            programs_path=programmes,
            applications_path=applications,
            candidates_path=candidates,
            state_path=state,
            fetcher=lambda _url: "<html></html>",
        )

    assert not candidates.exists()
    assert not state.exists()


def test_fetch_catalog_extracts_pdf_text(monkeypatch) -> None:
    page = FetchedPage(
        body="%PDF binary text",
        raw_bytes=b"pdf bytes",
        final_url="https://example.edu/catalog.pdf",
        status_code=200,
        content_type="application/pdf",
        charset="utf-8",
        bytes_read=9,
        truncated=False,
    )
    monkeypatch.setattr(programme_discovery, "fetch_page", lambda *args, **kwargs: page)
    monkeypatch.setattr(
        programme_discovery,
        "extract_fetched_text",
        lambda fetched: "extracted official PDF text",
        raising=False,
    )

    assert programme_discovery.fetch_catalog(page.final_url) == (
        "extracted official PDF text"
    )


def test_fetch_catalog_extracts_xlsx_rows(monkeypatch) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Programmes"
    sheet.append(["Faculty", "Programme"])
    sheet.append(["School of Science", "Mathematics"])
    output = BytesIO()
    workbook.save(output)
    page = FetchedPage(
        body="PK zip text",
        raw_bytes=output.getvalue(),
        final_url="https://example.edu/catalog.xlsx",
        status_code=200,
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        charset="utf-8",
        bytes_read=len(output.getvalue()),
        truncated=False,
    )
    monkeypatch.setattr(programme_discovery, "fetch_page", lambda *args, **kwargs: page)

    payload = json.loads(programme_discovery.fetch_catalog(page.final_url))

    assert payload == {
        "worksheets": [
            {
                "name": "Programmes",
                "rows": [
                    ["Faculty", "Programme"],
                    ["School of Science", "Mathematics"],
                ],
            }
        ]
    }


CUHK_HTML = """
<html><body>
  <p>Application Commencement Date*: 1 September 2025 at 09:00 a.m.</p>
  <div class="view-grouping">
    <div class="view-grouping-header">Faculty of Engineering</div>
    <div class="view-grouping-content">
      <div class="collapse-item">
        <div class="collapse-item-header"><span>Computer Science and Engineering</span></div>
        <div class="collapse-item-content">
          <div class="col-12">
            <h3>Research Programmes</h3>
            <div class="MAinAnthropology my-4">
              <div class="title-bg">MPhil-PhD in Computer Science</div>
              <div class="content-bg"><p>Main Round: 1 December 2025</p></div>
            </div>
          </div>
          <div class="col-12">
            <h3>Taught Programmes</h3>
            <div class="MAinAnthropology my-4">
              <div class="title-bg">MSc in Computer Science</div>
              <div class="content-bg"><p>31 January 2026</p></div>
            </div>
            <div class="MAinAnthropology my-4">
              <div class="title-bg">MSc in Artificial Intelligence</div>
              <div class="content-bg">
                <p>1st round: 6 Oct 2025 (Mon)</p>
                <p>Final round: 26 Feb 2026 (Thurs)</p>
                <p>Applications submitted after 26 Feb 2026 may be considered.</p>
              </div>
            </div>
            <div class="MAinAnthropology my-4">
              <div class="title-bg">PgD in Financial Technology</div>
              <div class="content-bg"><p>Final round: 26 Feb 2026</p></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="view-grouping">
    <div class="view-grouping-header">Faculty of Business Administration</div>
    <div class="view-grouping-content">
      <div class="collapse-item">
        <div class="collapse-item-header"><span>Business Administration</span></div>
        <div class="collapse-item-content">
          <div class="col-12">
            <h3>Taught Programmes</h3>
            <div class="MAinAnthropology my-4">
              <div class="title-bg">Executive Master of Professional Accountancy</div>
              <div class="content-bg"><p>To be confirmed</p></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body></html>
"""


def test_cuhk_adapter_extracts_only_masters_and_deadline_rounds() -> None:
    adapter = CUHKAdapter(minimum_expected_programmes=1)

    catalog = adapter.parse_catalog(CUHK_HTML)

    assert catalog.application_opens_at == "2025-09-01"
    assert [item.id for item in catalog.programmes] == [
        "cuhk-artificial-intelligence-msc",
        "cuhk-computer-science-msc",
        "cuhk-professional-accountancy-executive-master",
    ]
    ai = next(item for item in catalog.programmes if "artificial" in item.id)
    assert [(window.round, window.closes_at) for window in ai.windows] == [
        ("1st round", "2025-10-06"),
        ("Final round", "2026-02-26"),
    ]
    assert ai.faculty == "Faculty of Engineering"
    assert ai.department == "Computer Science and Engineering"
    accountancy = next(item for item in catalog.programmes if "accountancy" in item.id)
    assert accountancy.windows == []
    assert accountancy.parse_status == "no-deadline"


def test_cuhk_adapter_classifies_source_cycle_transition() -> None:
    html = CUHK_HTML.replace("1 September 2025", "1 September 2026")

    catalog = CUHKAdapter(minimum_expected_programmes=1).parse_catalog(html)

    assert catalog.application_opens_at == "2026-09-01"
    assert catalog.warnings == [
        {
            "reason": "SOURCE_CYCLE_TRANSITION",
            "message": (
                "CUHK has published a 2026-09-01 application commencement date, "
                "but the latest programme deadline still belongs to the previous "
                "cycle (2026-02-26)."
            ),
            "sourceUrl": "https://www.gs.cuhk.edu.hk/admissions/application-deadline",
            "applicationOpensAt": "2026-09-01",
            "latestPublishedDeadline": "2026-02-26",
        }
    ]


def test_cuhk_adapter_rejects_implausibly_small_catalog() -> None:
    adapter = CUHKAdapter(minimum_expected_programmes=10)

    with pytest.raises(ValueError, match="catalog only contained"):
        adapter.parse_catalog(CUHK_HTML)


def test_early_round_before_shared_commencement_requires_opening_review(
    tmp_path,
) -> None:
    html = CUHK_HTML.replace(
        "To be confirmed",
        "1 August 2025 (Early Round)",
    )
    adapter = CUHKAdapter(minimum_expected_programmes=1)
    programs_path = tmp_path / "programs.json"
    candidates_path = tmp_path / "candidates.json"
    state_path = tmp_path / "state.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")

    discover_programmes(
        adapter,
        programs_path=programs_path,
        candidates_path=candidates_path,
        state_path=state_path,
        fetcher=lambda url: html,
    )

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    accountancy = next(
        item for item in candidates if "accountancy" in item["programme"]["id"]
    )
    assert accountancy["windows"] == [
        {
            "intake": "September 2026",
            "round": "Early round",
            "applicantCategories": ["all"],
            "opensAt": None,
            "opensAtBasis": "missing",
            "closesAt": "2025-08-01",
            "sourceUrl": "https://www.gs.cuhk.edu.hk/admissions/application-deadline",
        }
    ]
    assert "programme-specific opening date" in accountancy["reviewReason"]


def test_discovery_creates_candidates_without_mutating_programmes(
    tmp_path,
) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs = {
        "programs": [
            {
                "id": "cuhk-computer-science-msc",
                "universityId": "the-chinese-university-of-hong-kong",
                "name": "MSc in Computer Science",
                "degreeType": "MSc",
                "faculty": "Computer Science and Engineering",
                "applicationUrl": "https://example.test/apply",
                "sourceUrl": "https://example.test/deadlines",
            }
        ]
    }
    programs_path.write_text(json.dumps(programs), encoding="utf-8")
    applications_path.write_text(
        json.dumps({"meta": {}, "applications": []}), encoding="utf-8"
    )
    adapter = CUHKAdapter(minimum_expected_programmes=1)

    report = discover_programmes(
        adapter,
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: CUHK_HTML,
    )

    assert report["status"] == "ok"
    assert report["catalogProgrammes"] == 3
    assert report["newCandidates"] == 2
    assert report["newWindowCandidates"] == 1
    assert report["changedWindowCandidates"] == 0
    assert report["adapterDiagnostics"]["transport"] == {
        "requests": 1,
        "directSuccesses": 1,
        "directFailures": 0,
        "fallbackEnabled": False,
        "fallbackLimit": 3,
        "fallbackAttempts": 0,
        "fallbackSuccesses": 0,
        "fallbackFailures": 0,
        "fallbackBudgetExhausted": 0,
        "failureKinds": {},
    }
    assert json.loads(programs_path.read_text(encoding="utf-8")) == programs
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    assert [item["programme"]["id"] for item in candidates] == [
        "cuhk-artificial-intelligence-msc",
        "cuhk-professional-accountancy-executive-master",
    ]
    assert candidates[0]["windows"][0]["opensAt"] == "2025-09-01"
    assert candidates[1]["reviewReason"] == "No application deadline was parsed."
    window_candidates = json.loads(window_candidates_path.read_text(encoding="utf-8"))[
        "items"
    ]
    assert len(window_candidates) == 1
    assert window_candidates[0]["type"] == "adapter-new-window"
    assert window_candidates[0]["openingBasis"] == "official"
    assert window_candidates[0]["record"]["scopeId"] == "cuhk-computer-science-msc"
    assert window_candidates[0]["record"]["opensAt"] == "2025-09-01"
    assert window_candidates[0]["record"]["closesAt"] == "2026-01-31"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["universities"][adapter.university_id]["itemCount"] == 3

    repeated = discover_programmes(
        adapter,
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: CUHK_HTML,
    )

    assert repeated["newCandidates"] == 0
    assert repeated["pendingCandidates"] == 2
    assert repeated["newWindowCandidates"] == 0
    assert repeated["pendingWindowCandidates"] == 1


def test_discovery_uses_shared_browser_fallback_and_reports_transport(
    tmp_path,
) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    programs_path.write_text('{"programs": []}', encoding="utf-8")
    applications_path.write_text(
        '{"meta": {}, "applications": []}',
        encoding="utf-8",
    )
    direct_calls = []
    browser_calls = []

    def blocked(url: str) -> str:
        direct_calls.append(url)
        raise FetchFailure("HTTP 403", kind="blocked", status_code=403)

    report = discover_programmes(
        CUHKAdapter(minimum_expected_programmes=1),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=tmp_path / "programme-candidates.json",
        state_path=tmp_path / "programme-catalog-state.json",
        fetcher=blocked,
        browser_fetcher=lambda url: browser_calls.append(url) or CUHK_HTML,
        browser_fallback_limit=1,
        dry_run=True,
    )

    assert direct_calls == [CUHKAdapter.catalog_url]
    assert browser_calls == [CUHKAdapter.catalog_url]
    assert report["catalogProgrammes"] == 3
    assert report["adapterDiagnostics"]["transport"] == {
        "requests": 1,
        "directSuccesses": 0,
        "directFailures": 1,
        "fallbackEnabled": True,
        "fallbackLimit": 1,
        "fallbackAttempts": 1,
        "fallbackSuccesses": 1,
        "fallbackFailures": 0,
        "fallbackBudgetExhausted": 0,
        "failureKinds": {"blocked": 1},
    }


def test_recurring_policy_dates_publish_separately_not_as_exact_windows(
    tmp_path,
) -> None:
    class RecurringPolicyAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "Summer semester 2027"
        replace_pending_candidates = True

        def parse_catalog(self, _html):
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="",
                        department="",
                        source_url=self.catalog_url,
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Recurring application period",
                                opens_at="2026-10-01",
                                closes_at="2026-11-30",
                                intake=self.intake,
                                opens_at_basis="official-recurring-policy",
                            )
                        ],
                        deadline_text="Summer semester: 01.10. - 30.11.",
                        parse_status="incomplete",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": "example-msc",
                        "universityId": "example-university",
                        "name": "Example MSc",
                        "applicationUrl": "https://example.edu/apply",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")

    report = discover_programmes(
        RecurringPolicyAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda _url: "<main></main>",
    )

    assert report["observedWindowCount"] == 1
    assert report["exactWindowCount"] == 0
    assert report["recurringPolicyWindowCount"] == 1
    assert report["missingOpeningDateCount"] == 0
    assert report["windowStatus"] == "recurring-policy"
    assert report["publishedRecurringPolicyRecords"] == 1
    assert report["pendingCandidates"] == 0
    assert report["pendingGuidanceCandidates"] == 0
    assert not window_candidates_path.exists()
    guidance = json.loads(candidates_path.read_text(encoding="utf-8"))["items"][0]
    assert guidance["type"] == "known-programme-recurring-policy"
    assert guidance["status"] == "published"
    assert guidance["windows"][0]["opensAtBasis"] == "official-recurring-policy"
    assert "published separately" in guidance["reviewReason"]


def test_dedicated_adapter_can_replace_stale_pending_candidates(tmp_path) -> None:
    class ReplacingAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "September 2027"
        application_opens_at_basis = "missing"
        replace_pending_candidates = True

        def parse_catalog(self, _html):
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-current-msc",
                        name="Current MSc",
                        degree_type="MSc",
                        faculty="",
                        department="",
                        source_url="https://example.edu/programmes/current",
                        application_url="https://example.edu/apply",
                        windows=[],
                        deadline_text="No exact deadline published.",
                        parse_status="no-deadline",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    candidates_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "new-programme:example-stale-msc",
                        "type": "new-programme",
                        "universityId": "example-university",
                        "status": "pending",
                    },
                    {
                        "id": "new-programme:example-reviewed-msc",
                        "type": "new-programme",
                        "universityId": "example-university",
                        "status": "approved",
                    },
                    {
                        "id": "new-programme:other-msc",
                        "type": "new-programme",
                        "universityId": "other-university",
                        "status": "pending",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    window_candidates_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "adapter-window:example-stale",
                        "type": "adapter-new-window",
                        "universityId": "example-university",
                        "status": "pending",
                    },
                    {
                        "id": "adapter-window:example-reviewed",
                        "type": "adapter-new-window",
                        "universityId": "example-university",
                        "status": "approved",
                    },
                    {
                        "id": "adapter-window:other",
                        "type": "adapter-new-window",
                        "universityId": "other-university",
                        "status": "pending",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    discover_programmes(
        ReplacingAdapter(),
        programs_path=programs_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: "",
    )

    candidate_ids = {
        item["id"]
        for item in json.loads(candidates_path.read_text(encoding="utf-8"))["items"]
    }
    assert candidate_ids == {
        "new-programme:example-current-msc",
        "new-programme:example-reviewed-msc",
        "new-programme:other-msc",
    }
    window_candidate_ids = {
        item["id"]
        for item in json.loads(window_candidates_path.read_text(encoding="utf-8"))[
            "items"
        ]
    }
    assert window_candidate_ids == {
        "adapter-window:example-reviewed",
        "adapter-window:other",
    }


def test_known_programme_missing_opening_stays_in_guidance_queue(tmp_path) -> None:
    class GuidanceAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "September 2027"
        application_opens_at_basis = "missing"
        replace_pending_candidates = True

        def parse_catalog(self, _html):
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-known-msc",
                        name="Known MSc",
                        degree_type="MSc",
                        faculty="Example Faculty",
                        department="",
                        source_url="https://example.edu/programmes/known",
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Final deadline",
                                closes_at="2027-08-01",
                            )
                        ],
                        deadline_text="Applications close on 1 August 2027.",
                        parse_status="incomplete",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": "example-known-msc",
                        "universityId": "example-university",
                        "name": "Known MSc",
                        "degreeType": "MSc",
                        "faculty": "Example Faculty",
                        "applicationUrl": "https://example.edu/apply",
                        "sourceUrl": "https://example.edu/programmes/known",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")

    report = discover_programmes(
        GuidanceAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda _: "",
    )

    candidate = json.loads(candidates_path.read_text(encoding="utf-8"))["items"][0]
    assert report["newCandidates"] == 0
    assert report["newGuidanceCandidates"] == 1
    assert report["pendingGuidanceCandidates"] == 1
    assert candidate["id"] == "known-programme-guidance:example-known-msc"
    assert candidate["type"] == "known-programme-window-guidance"
    assert candidate["windows"] == [
        {
            "intake": "September 2027",
            "round": "Final deadline",
            "applicantCategories": ["all"],
            "opensAt": None,
            "opensAtBasis": "missing",
            "closesAt": "2027-08-01",
            "sourceUrl": "https://example.edu/programmes/known",
        }
    ]


def test_shared_group_window_creates_one_candidate_for_multiple_programmes(
    tmp_path,
) -> None:
    class SharedGroupAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "Spring (March) 2027"
        known_programme_window_scope_type = "programme-group"
        known_programme_window_scope_id = "example-shared-admissions"

        def parse_catalog(self, _html):
            window = DiscoveredWindow(
                round="International admissions",
                applicant_categories=["international-students"],
                opens_at="2026-07-06",
                closes_at="2026-07-09",
                source_url="https://example.edu/admissions",
            )
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id=f"example-{name}-master",
                        name=f"Master's in {name.title()}",
                        degree_type="Master",
                        faculty="Graduate School",
                        department=name.title(),
                        source_url=f"https://example.edu/programmes/{name}",
                        application_url="https://example.edu/apply",
                        windows=[window],
                        deadline_text="One official central application window.",
                        parse_status="parsed",
                    )
                    for name in ("alpha", "beta")
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": f"example-{name}-master",
                        "universityId": "example-university",
                        "name": f"Master's in {name.title()}",
                        "degreeType": "Master",
                        "faculty": "Graduate School",
                        "applicationUrl": "https://example.edu/apply",
                        "sourceUrl": f"https://example.edu/programmes/{name}",
                    }
                    for name in ("alpha", "beta")
                ]
            }
        ),
        encoding="utf-8",
    )
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")

    report = discover_programmes(
        SharedGroupAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda _url: "<main></main>",
    )

    window_candidates = json.loads(window_candidates_path.read_text(encoding="utf-8"))[
        "items"
    ]
    assert report["newWindowCandidates"] == 1
    assert report["pendingWindowCandidates"] == 1
    assert len(window_candidates) == 1
    assert window_candidates[0]["record"]["scopeType"] == "programme-group"
    assert window_candidates[0]["record"]["scopeId"] == "example-shared-admissions"


def test_known_programme_without_dates_stays_in_monitoring_not_review_queue() -> None:
    adapter = BaseProgrammeAdapter()
    adapter.university_id = "example-university"
    programme = DiscoveredProgramme(
        id="known-programme",
        name="Known programme",
        degree_type="MSc",
        faculty="Example University",
        department="",
        source_url="https://example.edu/programmes/known",
        application_url="https://example.edu/apply",
        windows=[],
        deadline_text="No exact dates are currently published.",
        parse_status="no-deadline",
    )

    assert (
        programme_discovery._known_programme_guidance_candidate(
            adapter,
            programme,
            None,
            "2026-07-30T00:00:00+00:00",
        )
        is None
    )


def test_known_programme_window_change_becomes_review_candidate(tmp_path) -> None:
    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": "cuhk-computer-science-msc",
                        "universityId": "the-chinese-university-of-hong-kong",
                        "name": "MSc in Computer Science",
                        "degreeType": "MSc",
                        "faculty": "Computer Science and Engineering",
                        "applicationUrl": "https://www.gs.cuhk.edu.hk/admissions/",
                        "sourceUrl": (
                            "https://www.gs.cuhk.edu.hk/admissions/application-deadline"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    applications_path.write_text(
        json.dumps(
            {
                "applications": [
                    {
                        "id": "cuhk-computer-science-msc-2026-main",
                        "universityId": "the-chinese-university-of-hong-kong",
                        "scopeType": "programme",
                        "scopeId": "cuhk-computer-science-msc",
                        "intake": "September 2026",
                        "intakeDetails": {
                            "label": "September 2026",
                            "cycleYear": 2026,
                            "term": "fall",
                            "startMonth": 9,
                        },
                        "round": "Main application period",
                        "applicantCategories": ["all"],
                        "opensAt": "2025-09-01",
                        "closesAt": "2026-01-15",
                        "applicationUrl": "https://www.gs.cuhk.edu.hk/admissions/",
                        "sourceUrl": (
                            "https://www.gs.cuhk.edu.hk/admissions/application-deadline"
                        ),
                        "verifiedAt": "2025-10-01",
                        "evidence": "Previous official deadline.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = discover_programmes(
        CUHKAdapter(minimum_expected_programmes=1),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: CUHK_HTML,
    )

    assert report["changedWindowCandidates"] == 1
    candidate = json.loads(window_candidates_path.read_text(encoding="utf-8"))["items"][
        0
    ]
    assert candidate["type"] == "adapter-window-change"
    assert candidate["record"]["id"] == "cuhk-computer-science-msc-2026-main"
    assert candidate["changes"]["closesAt"] == {
        "previous": "2026-01-15",
        "observed": "2026-01-31",
    }


def test_known_programme_inferred_opening_does_not_create_window_candidate(
    tmp_path,
) -> None:
    class InferredOpeningAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "September 2027"
        application_opens_at_basis = "inferred-cycle-default"

        def parse_catalog(self, _html):
            return DiscoveredCatalog(
                application_opens_at="2026-10-01",
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="",
                        department="",
                        source_url="https://example.edu/programmes/example",
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Main",
                                closes_at="2027-01-31",
                            )
                        ],
                        deadline_text="Applications close on 31 January 2027.",
                        parse_status="parsed",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": "example-msc",
                        "universityId": "example-university",
                        "name": "Example MSc",
                        "degreeType": "MSc",
                        "faculty": "",
                        "applicationUrl": "https://example.edu/apply",
                        "sourceUrl": "https://example.edu/programmes/example",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")

    report = discover_programmes(
        InferredOpeningAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: "<html></html>",
    )

    assert report["newWindowCandidates"] == 0
    assert not window_candidates_path.exists()


def test_unrelated_discovery_does_not_reorder_window_candidates(tmp_path) -> None:
    class EmptyAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"

        def parse_catalog(self, _html):
            return DiscoveredCatalog(application_opens_at=None, programmes=[])

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")
    original = {
        "meta": {"updatedAt": "2026-08-01T00:00:00+00:00"},
        "items": [
            {"id": "z-candidate", "universityId": "other", "status": "approved"},
            {"id": "a-candidate", "universityId": "other", "status": "approved"},
        ],
    }
    window_candidates_path.write_text(json.dumps(original), encoding="utf-8")

    discover_programmes(
        EmptyAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: "<html></html>",
    )

    assert json.loads(window_candidates_path.read_text(encoding="utf-8")) == original


def test_target_discovery_does_not_rewrite_unrelated_window_shard(tmp_path) -> None:
    class ExactAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "Fall 2027"

        def parse_catalog(self, _html):
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="Example faculty",
                        department="Example department",
                        source_url=self.catalog_url,
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Main",
                                opens_at="2026-09-01",
                                closes_at="2027-01-01",
                                intake=self.intake,
                            )
                        ],
                        deadline_text="Official dates",
                        parse_status="parsed",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": "example-msc",
                        "universityId": "example-university",
                        "name": "Example MSc",
                        "degreeType": "MSc",
                        "faculty": "Example faculty",
                        "applicationUrl": "https://example.edu/apply",
                        "sourceUrl": "https://example.edu/programmes",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")
    window_candidates_path.write_text(
        json.dumps(
            {
                "meta": {},
                "items": [
                    {"id": "z-candidate", "universityId": "other"},
                    {"id": "a-candidate", "universityId": "other"},
                ],
            }
        ),
        encoding="utf-8",
    )
    partition_json_file(
        window_candidates_path,
        collection_key="items",
        group_key="universityId",
    )
    other_shard = tmp_path / "window-candidates/by-university/other.json"
    before = other_shard.read_bytes()

    discover_programmes(
        ExactAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        window_candidates_path=window_candidates_path,
        state_path=state_path,
        fetcher=lambda url: "<html></html>",
    )

    assert other_shard.read_bytes() == before


def test_unrelated_discovery_does_not_reorder_programme_candidates(tmp_path) -> None:
    class EmptyAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"

        def parse_catalog(self, _html):
            return DiscoveredCatalog(application_opens_at=None, programmes=[])

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")
    original = {
        "meta": {"updatedAt": "2026-08-01T00:00:00+00:00"},
        "items": [
            {"id": "z-candidate", "universityId": "other", "status": "approved"},
            {"id": "a-candidate", "universityId": "other", "status": "approved"},
        ],
    }
    candidates_path.write_text(json.dumps(original), encoding="utf-8")

    discover_programmes(
        EmptyAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=candidates_path,
        state_path=state_path,
        fetcher=lambda url: "<html></html>",
    )

    written = json.loads(candidates_path.read_text(encoding="utf-8"))
    assert written["items"] == original["items"]
