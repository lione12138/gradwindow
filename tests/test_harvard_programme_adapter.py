from __future__ import annotations

import pytest

from gradwindow.programme_adapters.harvard import (
    APPLICATION_URL,
    MASTER_FILTER_URLS,
    HarvardAdapter,
    _official_intake,
)

FIRST_PAGE_HTML = """
<html><body>
  <a href="/programs?page=1">Page 2</a>
  <div class="views-row">
    <div class="program-title">
      <h3><a href="/program/computational-science-and-engineering">
        Computational Science and Engineering
      </a></h3>
    </div>
    <div class="field field--node-field-area">
      <div class="field-label">Area of Study Within</div>
      <div class="field__item">Engineering and Applied Sciences</div>
    </div>
    <div class="paragraph paragraph--type--degree">
      <div class="field--paragraph-field-degree-type">Master of Engineering (ME)</div>
      <time datetime="2026-12-01T22:00:00Z">Dec 01, 2026 | 05:00 pm</time>
    </div>
    <div class="paragraph paragraph--type--degree">
      <div class="field--paragraph-field-degree-type">Master of Science (SM)</div>
      <time datetime="2026-12-01T22:00:00Z">Dec 01, 2026 | 05:00 pm</time>
    </div>
    <div class="paragraph paragraph--type--degree">
      <div class="field--paragraph-field-degree-type">Doctor of Philosophy (PhD)</div>
      <time datetime="2026-12-15T22:00:00Z">Dec 15, 2026 | 05:00 pm</time>
    </div>
  </div>
</body></html>
"""

SECOND_PAGE_HTML = """
<html><body>
  <div class="views-row">
    <div class="program-title">
      <h3><a href="/program/msmba">MS/MBA</a></h3>
    </div>
    <div class="paragraph paragraph--type--degree">
      <div class="field--paragraph-field-degree-type">Master of Science (SM)</div>
    </div>
  </div>
</body></html>
"""


def test_harvard_adapter_extracts_master_degree_deadlines_across_pages() -> None:
    adapter = HarvardAdapter(minimum_expected_programmes=1)
    fetched = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        if url == APPLICATION_URL:
            return "<main>The 2027–2028 academic year application to degree programs is open.</main>"
        if url == MASTER_FILTER_URLS[2]:
            return SECOND_PAGE_HTML
        return FIRST_PAGE_HTML

    catalog = adapter.parse_catalog_from_fetcher(fetcher)

    assert catalog.application_opens_at is None
    assert [item.id for item in catalog.programmes] == [
        "harvard-computational-science-and-engineering-me",
        "harvard-computational-science-and-engineering-sm",
        "harvard-ms-mba-sm",
    ]
    cse_me = catalog.programmes[0]
    assert cse_me.name == "ME Computational Science and Engineering"
    assert cse_me.degree_type == "ME"
    assert cse_me.faculty == "Engineering and Applied Sciences"
    assert (
        cse_me.source_url
        == "https://gsas.harvard.edu/program/computational-science-and-engineering"
    )
    assert cse_me.parse_status == "incomplete"
    assert [
        (window.round, window.intake, window.closes_at, window.opens_at)
        for window in cse_me.windows
    ] == [("Main deadline", "Fall 2027", "2026-12-01", None)]

    msmba = catalog.programmes[-1]
    assert msmba.name == "SM MS/MBA"
    assert msmba.parse_status == "no-deadline"
    assert msmba.windows == []
    assert fetched == [APPLICATION_URL, *MASTER_FILTER_URLS]


@pytest.mark.parametrize("years", ["2027–2028", "2028-2029"])
def test_harvard_cycle_comes_from_explicit_open_notice(years):
    assert (
        _official_intake(
            f"<main>The {years} academic year application to degree programs is open.</main>"
        )
        == f"Fall {years[:4]}"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Applications become available in September.",
        "2027–2029 academic year application to degree programs is open",
        "2026–2027 academic year application to degree programs is open. 2027–2028 academic year application to degree programs is open",
    ],
)
def test_harvard_rejects_missing_or_ambiguous_cycle(text):
    with pytest.raises(ValueError):
        _official_intake(f"<main>{text}</main>")


def test_harvard_rejects_deadlines_from_previous_cycle():
    adapter = HarvardAdapter(minimum_expected_programmes=1)
    with pytest.raises(ValueError, match="deadline did not match"):
        adapter.parse_catalog_from_fetcher(
            lambda url: (
                "<main>2028–2029 academic year application to degree programs is open</main>"
                if url == APPLICATION_URL
                else FIRST_PAGE_HTML
            )
        )
