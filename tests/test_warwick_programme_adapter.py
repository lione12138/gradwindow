import json

import pytest

from gradwindow.programme_adapters.warwick import (
    API_URL,
    APPLICATION_URL,
    CATALOG_URL,
    WarwickAdapter,
)


def test_warwick_current_json_directory_preserves_ids_and_filters():
    def item(name="Computer Science MSc", href="msc-computer-science", categories=None):
        return {
            "title": name,
            "categories": categories or ["Study level: Postgraduate Taught (sl02)"],
            "parsedContentBody": f'<h3><a href="{href}">{name}</a></h3><p class="qualification">Master of Science (MSc)</p>',
        }

    rows = [
        item(),
        item(),
        item(
            categories=["Visibility: Hidden", "Study level: Postgraduate Taught (sl02)"]
        ),
        item(categories=["Study level: Postgraduate Research (sl03)"]),
        item(href="https://example.com/course"),
    ]
    catalog = WarwickAdapter(1).parse_json(json.dumps({"items": rows}))
    assert [p.id for p in catalog.programmes] == ["warwick-computer-science-msc"]
    assert catalog.programmes[0].source_url == CATALOG_URL + "msc-computer-science"
    assert not catalog.programmes[0].windows


def test_warwick_fetches_api_for_current_shell_and_keeps_masters_only():
    items = [
        {
            "categories": ["Study level: Postgraduate Taught (sl02)"],
            "parsedContentBody": '<h3><a href="msc-data">Data Science (MSc/PGDip/PGCert)</a></h3><p class="qualification">Master of Science (MSc)</p>',
        },
        {
            "categories": ["Study level: Postgraduate Taught (sl02)"],
            "parsedContentBody": '<h3><a href="certificate">Teaching PGCert</a></h3><p class="qualification">Postgraduate Certificate (PGCert)</p>',
        },
    ]
    pages = {
        CATALOG_URL: '<div id="course-container"></div>',
        APPLICATION_URL: "Applications for most courses. The on-time deadline.",
        API_URL: json.dumps({"items": items}),
    }
    catalog = WarwickAdapter(1).parse_catalog_from_fetcher(pages.__getitem__)
    assert [p.id for p in catalog.programmes] == ["warwick-data-science-msc"]
    with pytest.raises(ValueError, match="expected at least 2"):
        WarwickAdapter(2).parse_catalog_from_fetcher(pages.__getitem__)


CATALOGUE = """
<div class="feed-item-list-item"><h2>Advanced Mechanical Engineering MSc</h2>
  <div class="feed-item-abstract"><div>Postgraduate Taught</div>
    <p><a href="https://warwick.ac.uk/study/postgraduate/courses/msc-advanced-mechanical-engineering">Advanced Mechanical Engineering (MSc)</a></p></div></div>
<div class="feed-item-list-item"><h2>Computer Science MSc</h2>
  <div class="feed-item-abstract"><div>Postgraduate Taught</div>
    <p><a href="https://warwick.ac.uk/study/postgraduate/courses/msc-computer-science">Computer Science (MSc)</a></p></div></div>
<div class="feed-item-list-item"><h2>Mathematics PhD</h2>
  <div class="feed-item-abstract"><div>Postgraduate Research</div>
    <p><a href="https://warwick.ac.uk/study/postgraduate/courses/phd-mathematics">Mathematics (PhD)</a></p></div></div>
"""


def test_warwick_adapter_discovers_taught_masters_and_reuses_cs_id() -> None:
    catalog = WarwickAdapter(minimum_expected_programmes=2).parse_catalog(CATALOGUE)

    assert [item.id for item in catalog.programmes] == [
        "warwick-advanced-mechanical-engineering-msc",
        "warwick-computer-science-msc",
    ]
    assert [item.degree_type for item in catalog.programmes] == ["MSc", "MSc"]
    assert all(item.windows == [] for item in catalog.programmes)


def test_warwick_adapter_rejects_a_truncated_catalogue() -> None:
    try:
        WarwickAdapter(minimum_expected_programmes=3).parse_catalog(CATALOGUE)
    except ValueError as error:
        assert "expected at least 3" in str(error)
    else:
        raise AssertionError("truncated Warwick catalogue was accepted")


def test_warwick_adapter_checks_the_official_application_policy() -> None:
    pages = {
        CATALOG_URL: CATALOGUE,
        APPLICATION_URL: (
            "Applications for most courses starting in September and October 2026 "
            "are now open. The on-time deadline is 2 August 2026."
        ),
    }

    catalog = WarwickAdapter(minimum_expected_programmes=2).parse_catalog_from_fetcher(
        lambda url: pages[url]
    )

    assert len(catalog.programmes) == 2
    with pytest.raises(ValueError, match="application policy"):
        WarwickAdapter(minimum_expected_programmes=2).parse_catalog_from_fetcher(
            lambda url: CATALOGUE if url == CATALOG_URL else "Unavailable"
        )
