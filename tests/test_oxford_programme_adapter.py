from __future__ import annotations

import json

import pytest
from bs4 import BeautifulSoup

from gradwindow.programme_adapters.oxford import OxfordAdapter


def _finder_page(*cards: str, total: int, items_per_page: int = 12) -> str:
    config = {
        "listing": {
            "3405": {
                "paragraph_id": "3405",
                "items_per_page": items_per_page,
                "default_sorts": [
                    {
                        "search_key": "search_api_relevance",
                        "direction": "desc",
                    },
                    {
                        "search_key": "course_subject_sort",
                        "direction": "asc",
                    },
                ],
            }
        }
    }
    return f"""
    <html><body><main>
      <h1>Find your postgraduate course</h1>
      <div data-js-filter-listing data-js-filter-listing-id="3405">
        <p>Showing 1 - {min(items_per_page, total)} of {total} Results</p>
        {"".join(cards)}
      </div>
      <script type="application/json" data-drupal-selector="drupal-settings-json">
        {json.dumps(config)}
      </script>
    </main></body></html>
    """


def _course_card(
    *,
    title: str,
    slug: str,
    statuses: tuple[tuple[str, str], ...],
    description: str = "Official Oxford graduate course.",
) -> str:
    tags = "".join(
        f'<div data-component-id="numiko:tag"><span>{mode}: {status}</span></div>'
        for mode, status in statuses
    )
    return f"""
    <article>
      <div class="course-statuses">{tags}</div>
      <h3><a href="/admissions/graduate/courses/{slug}"><span>{title}</span></a></h3>
      <p>{description}</p>
      <dl><dt>Expected start date:</dt><dd>October 2026</dd></dl>
    </article>
    """


ADVANCED_CARD = _course_card(
    title="MSc in Advanced Computer Science",
    slug="msc-advanced-computer-science",
    statuses=(("Full time", "Closed"),),
)
TRANSLATIONAL_CARD = _course_card(
    title="MSc in Translational Health Sciences",
    slug="msc-translational-health-sciences",
    statuses=(("Full time", "Closed"), ("Part time", "Closed")),
)
INTEGRATED_CARD = _course_card(
    title="MPhil + DPhil in Economics",
    slug="mphil-dphil-economics",
    statuses=(("Full time", "Closed"),),
)
BPHIL_CARD = _course_card(
    title="BPhil in Philosophy",
    slug="bphil-philosophy",
    statuses=(("Full time", "Closed"),),
)
SBS_CARD = _course_card(
    title="MSc in Financial Economics",
    slug="msc-financial-economics",
    statuses=(("Full time", "Apply directly"),),
)

OXFORD_FINDER_PAGE = _finder_page(
    ADVANCED_CARD,
    TRANSLATIONAL_CARD,
    INTEGRATED_CARD,
    total=5,
    items_per_page=3,
)
OXFORD_API_PAGE = json.dumps({"results": [BPHIL_CARD, SBS_CARD]})

OXFORD_DETAIL = """
<html><body><main>
  <h1>MSc in Translational Health Sciences</h1>
  <div class="course-modes">
    <div class="mode-card">
      <h2>Full time</h2>
      <div><span>Open</span></div>
      <div class="application-status">
        <p>Application deadline: Tuesday 2 December 2026 at 12:00 midday UK time.</p>
      </div>
      <dl><dt>Expected start date</dt><dd>October 2027</dd></dl>
    </div>
    <div class="mode-card">
      <h2>Part time</h2>
      <div><span>Open</span></div>
      <div class="application-status">
        <p>Application deadline: Wednesday 6 January 2027 at 12:00 midday UK time.</p>
      </div>
      <dl><dt>Expected start date</dt><dd>October 2027</dd></dl>
    </div>
  </div>
  <section>
    <h2>Funding and costs</h2>
    <p>A separate funding deadline is 30 September 2026.</p>
  </section>
</main></body></html>
"""


def test_oxford_browser_wait_selector_matches_current_course_cards() -> None:
    soup = BeautifulSoup(OXFORD_FINDER_PAGE, "html.parser")
    selector = OxfordAdapter.browser_wait_for_selectors[OxfordAdapter.catalog_url]

    assert len(soup.select(selector)) == 3


def test_oxford_adapter_uses_current_finder_api_and_preserves_study_modes() -> None:
    calls: list[str] = []

    def fetcher(url: str) -> str:
        calls.append(url)
        if "/api/listing/3405" in url:
            return OXFORD_API_PAGE
        if url == OxfordAdapter.catalog_url:
            return OXFORD_FINDER_PAGE
        raise AssertionError(f"closed courses must not fetch detail pages: {url}")

    catalog = OxfordAdapter(
        minimum_expected_programmes=3,
        detail_workers=1,
    ).parse_catalog_from_fetcher(fetcher)

    assert [item.id for item in catalog.programmes] == [
        "oxford-advanced-computer-science-msc-full-time",
        "oxford-philosophy-bphil-full-time",
        "oxford-translational-health-sciences-msc-full-time",
        "oxford-translational-health-sciences-msc-part-time",
    ]
    assert [
        item.name for item in catalog.programmes if "Translational" in item.name
    ] == [
        "MSc in Translational Health Sciences (Full time)",
        "MSc in Translational Health Sciences (Part time)",
    ]
    assert all(item.parse_status == "no-deadline" for item in catalog.programmes)
    assert all("Closed" in item.deadline_text for item in catalog.programmes)
    assert len([url for url in calls if "/api/listing/3405" in url]) == 1
    assert all("courses-a-z-listing" not in url for url in calls)


def test_oxford_adapter_fetches_open_detail_once_and_scopes_deadlines_by_mode() -> None:
    open_card = _course_card(
        title="MSc in Translational Health Sciences",
        slug="msc-translational-health-sciences",
        statuses=(("Full time", "Open"), ("Part time", "Open")),
    )
    finder_page = _finder_page(open_card, total=1)
    detail_calls: list[str] = []

    def fetcher(url: str) -> str:
        if url == OxfordAdapter.catalog_url:
            return finder_page
        detail_calls.append(url)
        return OXFORD_DETAIL

    catalog = OxfordAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
    ).parse_catalog_from_fetcher(fetcher)

    assert detail_calls == [
        "https://www.ox.ac.uk/admissions/graduate/courses/"
        "msc-translational-health-sciences"
    ]
    assert [
        (item.id, item.windows[0].closes_at, item.windows[0].intake)
        for item in catalog.programmes
    ] == [
        (
            "oxford-translational-health-sciences-msc-full-time",
            "2026-12-02",
            "October 2027",
        ),
        (
            "oxford-translational-health-sciences-msc-part-time",
            "2027-01-06",
            "October 2027",
        ),
    ]
    assert all(item.parse_status == "incomplete" for item in catalog.programmes)
    assert all("2026-09-30" not in item.deadline_text for item in catalog.programmes)


def test_oxford_adapter_rejects_unrendered_or_partial_current_finder() -> None:
    empty_current_page = _finder_page(total=0)

    with pytest.raises(ValueError, match="expected at least 3"):
        OxfordAdapter(minimum_expected_programmes=3).parse_catalog(empty_current_page)
