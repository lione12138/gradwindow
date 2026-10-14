"""Reduced date-section markup observed on UCL Advanced Materials, 2026-10-14."""

from dataclasses import replace

import pytest

from gradwindow.http_client import FetchFailure
from gradwindow.programme_adapters.base import DiscoveredCatalog, DiscoveredProgramme
from gradwindow.programme_adapters.ucl import CATALOG_URL, UCLAdapter
from gradwindow.programme_adapters.ucl_detail import inspect_detail, monitor_details

HTML = """<h1 class="course-hero__title">Advanced Materials Science MSc</h1>
<div id="key-information">
<div class="key-info-item"><span class="key-info-item__label">Application deadlines</span>
<div class="key-info-item__value">To be confirmed.</div></div>
<div class="key-info-item"><span class="key-info-item__label">Course starts</span>
<div class="key-info-item__value">September 2027</div></div></div>
<section id="apply"><div class="apply-chooser">
<p>You are applying for the Advanced Materials Science MSc course.</p>
<a href="/study/applying">Application guidelines</a>
<div class="apply-chooser__slot-message"><p>The course application dates are to be confirmed.</p></div>
</div></section>"""


def programme(suffix="advanced-materials-science-msc"):
    url = f"{CATALOG_URL}/{suffix}"
    return DiscoveredProgramme(
        id=f"ucl-{suffix}",
        name="Advanced Materials Science MSc",
        degree_type="MSc",
        faculty="",
        department="",
        source_url=url,
        application_url=url,
        windows=[],
        deadline_text="",
        parse_status="no-deadline",
        available_intakes=["September 2027"],
    )


def test_pending_requires_official_scoped_sections():
    result = inspect_detail(HTML, programme())
    assert result["status"] == "dates-to-be-confirmed"
    assert len(result["evidenceHash"]) == 64


@pytest.mark.parametrize(
    "old,new",
    [
        ("September 2027", "September 2026"),
        ("Advanced Materials Science MSc", "Unrelated MSc"),
        ("key-information", "missing-section"),
    ],
)
def test_wrong_page_or_cycle_rejected(old, new):
    with pytest.raises(ValueError):
        inspect_detail(HTML.replace(old, new), programme())


def test_changed_deadline_needs_review_never_creates_window():
    # Synthetic change, not a claimed UCL date.
    html = HTML.replace("To be confirmed.", "30 June 2027")
    catalog = DiscoveredCatalog(None, [programme()])
    monitor_details(catalog, lambda _: html, {}, budget=1)
    assert (
        catalog.adapter_state["detailMonitor"][programme().source_url]["status"]
        == "needs-date-review"
    )
    assert catalog.programmes[0].windows == []


def test_budget_rotation_and_option_exclusion():
    records = [programme(str(i)) for i in range(3)]
    records += [
        programme("parent?option=TMS123"),
        replace(programme(), source_url=CATALOG_URL),
    ]
    catalog = DiscoveredCatalog(None, records)
    calls = []

    def fetch(url):
        calls.append(url)
        return HTML

    monitor_details(catalog, fetch, {}, budget=1)
    previous = catalog.adapter_state["detailMonitor"]
    monitor_details(catalog, fetch, previous, budget=1)
    assert calls == [records[0].source_url, records[1].source_url]
    assert catalog.diagnostics["detailMonitor"]["unvisitedPages"] == 1
    assert catalog.diagnostics["detailMonitor"]["excludedOptionRoutes"] == 1


def test_transport_failure_stops_batch_and_does_not_reuse_success():
    catalog = DiscoveredCatalog(None, [programme("a"), programme("b")])
    monitor_details(catalog, lambda _: HTML, {}, budget=2)
    previous = catalog.adapter_state["detailMonitor"]
    calls = []

    def blocked(url):
        calls.append(url)
        raise FetchFailure("rate limited", kind="blocked", status_code=429)

    monitor_details(catalog, blocked, previous, budget=2)
    assert len(calls) == 1
    failed = catalog.adapter_state["detailMonitor"][calls[0]]
    assert failed["status"] == "fetch-failed"
    assert "checkedAt" not in failed and "evidenceHash" not in failed


def test_old_intake_evidence_dropped_and_adapter_loads_state():
    catalog = DiscoveredCatalog(None, [programme()])
    monitor_details(catalog, lambda _: HTML, {}, budget=1)
    adapter = UCLAdapter()
    adapter.prepare_discovery({"adapterState": catalog.adapter_state})
    catalog.programmes[0].available_intakes = ["September 2028"]
    monitor_details(catalog, lambda _: HTML, adapter.detail_monitor, budget=0)
    assert catalog.adapter_state["detailMonitor"] == {}
    assert catalog.diagnostics["detailMonitor"]["unvisitedPages"] == 1


def test_default_adapter_connects_directory_and_detail_monitor():
    directory = f'''<p class="course-feed-listing-view__result-count">1 courses found</p>
    <article class="course-feed-listing-item">
    <span class="course-feed-listing-item__degree-level">Master of Science (MSc)</span>
    <div class="course-feed-listing-item__faculty">Faculty of Mathematical and Physical Sciences</div>
    <h2 class="course-feed-listing-item__heading--main">
    <a href="{programme().source_url}">Advanced Materials Science MSc</a></h2>
    <div class="course-feed-listing-item__start-dates">Start date: September 2027</div>
    </article>'''
    calls = []

    def fetch(url):
        calls.append(url)
        return directory if url == CATALOG_URL else HTML

    adapter = UCLAdapter(minimum_expected_courses=1, minimum_expected_programmes=1)
    catalog = adapter.parse_catalog_from_fetcher(fetch)
    assert calls == [CATALOG_URL, programme().source_url]
    assert (
        catalog.adapter_state["detailMonitor"][programme().source_url]["status"]
        == "dates-to-be-confirmed"
    )
    assert catalog.programmes[0].windows == []
