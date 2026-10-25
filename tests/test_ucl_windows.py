"""Real UCL 2027 DOM fixtures plus deliberately invalid mutations."""

from dataclasses import replace
from pathlib import Path

import pytest

from gradwindow.http_client import FetchFailure
from gradwindow.io import read_json, write_json
from gradwindow.programme_adapters.base import DiscoveredCatalog, DiscoveredProgramme
from gradwindow.programme_adapters.ucl import CATALOG_URL, UNIVERSITY_ID, UCLAdapter
from gradwindow.programme_adapters.ucl_detail import inspect_detail, monitor_details
from gradwindow.programme_discovery import discover_programmes

FIXTURES = Path(__file__).parent / "fixtures" / "ucl"


def record(
    slug="advanced-materials-science-msc", name="Advanced Materials Science MSc"
):
    return DiscoveredProgramme(
        id="ucl-" + slug,
        name=name,
        degree_type="MSc",
        faculty="Science",
        department="",
        source_url=CATALOG_URL + "/" + slug,
        application_url=CATALOG_URL + "/" + slug,
        windows=[],
        deadline_text="",
        parse_status="no-deadline",
        available_intakes=["September 2027"],
    )


def html(slug="advanced-materials-science-msc"):
    return (FIXTURES / (slug + ".html")).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "slug,name",
    [
        ("advanced-materials-science-msc", "Advanced Materials Science MSc"),
        ("law-and-finance-msc", "Law and Finance MSc"),
    ],
)
def test_official_single_and_multiple_mode_panels(slug, name):
    result = inspect_detail(html(slug), record(slug, name))
    assert result["status"] == "exact-windows"
    assert len(result["windows"]) == 2
    windows = {w["applicant_categories"][0]: w for w in result["windows"]}
    assert windows["requires-uk-study-visa"]["closes_at"] == "2027-06-25"
    assert windows["does-not-require-uk-study-visa"]["closes_at"] == "2027-08-27"
    assert all(
        w["opens_at"] == "2026-10-19"
        and w["intake"] == "September 2027"
        and w["opens_at_basis"] == "official"
        for w in windows.values()
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("Applicants who require a visa", "International students"),
        ("19 Oct 2026 - 25 Jun 2027", "October 2026 - 25 Jun 2027"),
        ("19 Oct 2026 - 25 Jun 2027", "19 Oct 2027 - 25 Jun 2027"),
        ("19 Oct 2026 - 25 Jun 2027", "19 Oct 2026 - 26 Jun 2027"),
        ("1813939200", "1814025600"),
        ('data-application-rolling="0"', 'data-application-rolling="1"'),
        ("Applications close at 5pm UK time", "Round 1 closes at 5pm UK time"),
        ("evision.ucl.ac.uk", "unrelated.example"),
        ("Full-time, September 2027", "Full-time, September 2026"),
        ("MSc Advanced Materials Science Full-time", "MSc Other Course Full-time"),
        ("apply-chooser__button", "unrecognised-button"),
    ],
)
def test_ambiguous_changed_or_incomplete_dates_are_review_only(old, new):
    result = inspect_detail(html().replace(old, new), record())
    assert result["status"] == "needs-date-review"
    assert "windows" not in result


def test_conflicting_study_mode_panels_are_not_collapsed():
    result = inspect_detail(
        html("law-and-finance-msc").replace("25 Jun 2027", "26 Jun 2027", 1),
        record("law-and-finance-msc", "Law and Finance MSc"),
    )
    assert result["status"] == "needs-date-review"


def test_multiple_intakes_are_not_given_the_same_dates():
    p = replace(record(), available_intakes=["September 2027", "January 2028"])
    with pytest.raises(ValueError, match="intake"):
        inspect_detail(html(), p)


def test_monitor_tracks_only_current_successes_and_never_reuses_windows():
    catalog = DiscoveredCatalog(
        None, [record(), replace(record("unvisited"), source_url=CATALOG_URL)]
    )
    monitor_details(catalog, lambda _: html(), {}, budget=1)
    assert len(catalog.programmes[0].windows) == 2
    previous = catalog.adapter_state["detailMonitor"]
    monitor_details(
        catalog, lambda _: pytest.fail("zero budget fetched"), previous, budget=0
    )
    assert catalog.programmes[0].windows == []
    assert catalog.diagnostics["detailSucceededProgrammeIds"] == []
    assert len(catalog.diagnostics["detailUnvisitedProgrammeIds"]) == 2
    assert catalog.adapter_state["detailMonitor"] == previous


@pytest.mark.parametrize("failure", ["budget", "transport", "parse"])
@pytest.mark.parametrize("known", [True, False])
def test_replacement_preserves_deferred_candidates_and_confirmation(
    tmp_path, failure, known
):
    p = record()
    directory = f'''<p class="course-feed-listing-view__result-count">1 courses found</p>
    <article class="course-feed-listing-item"><span class="course-feed-listing-item__degree-level">Master of Science (MSc)</span>
    <div class="course-feed-listing-item__faculty">Science</div>
    <h2 class="course-feed-listing-item__heading--main"><a href="{p.source_url}">{p.name}</a></h2>
    <div class="course-feed-listing-item__start-dates">Start date: September 2027</div></article>'''
    programs = tmp_path / "programs.json"
    write_json(
        programs,
        {
            "programs": [
                {
                    "id": p.id,
                    "universityId": UNIVERSITY_ID,
                    "applicationUrl": p.source_url,
                }
            ]
            if known
            else []
        },
    )
    paths = dict(
        programs_path=programs,
        applications_path=tmp_path / "applications.json",
        candidates_path=tmp_path / "programme-candidates.json",
        state_path=tmp_path / "state.json",
    )

    def fetch(url):
        return directory if url == CATALOG_URL else html()

    discover_programmes(UCLAdapter(1, 1), fetcher=fetch, **paths)
    path = tmp_path / (
        "window-candidates.json" if known else "programme-candidates.json"
    )
    before = read_json(path)["items"]
    assert len(before) == (2 if known else 1)
    assert all(c["status"] == "pending" for c in before)
    assert not paths["applications_path"].exists()

    def incomplete(url):
        if url == CATALOG_URL:
            return directory
        if failure == "transport":
            raise FetchFailure("rate limited", kind="blocked", status_code=429)
        return html().replace("Applicants who require a visa", "Unknown category")

    discover_programmes(
        UCLAdapter(1, 1, detail_refresh_budget=0 if failure == "budget" else 1),
        fetcher=incomplete,
        **paths,
    )
    assert read_json(path)["items"] == before
    if known:
        discover_programmes(UCLAdapter(1, 1), fetcher=fetch, **paths)
        after = read_json(path)["items"]
        assert all(c["confirmation"]["observationCount"] == 2 for c in after)
        assert [c["detectedAt"] for c in after] == [c["detectedAt"] for c in before]
