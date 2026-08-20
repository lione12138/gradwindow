from __future__ import annotations

import json

import pytest

from gradwindow.programme_adapters.bologna import BolognaAdapter
from gradwindow.programme_adapters.chalmers import ChalmersAdapter
from gradwindow.programme_adapters.kit import KITAdapter
from gradwindow.programme_adapters.ucd import UCDAdapter
from gradwindow.programme_adapters.vu_amsterdam import (
    APPLICATION_URL as VU_APPLICATION_URL,
)
from gradwindow.programme_adapters.vu_amsterdam import CATALOG_URL as VU_CATALOG_URL
from gradwindow.programme_adapters.vu_amsterdam import VUAmsterdamAdapter


@pytest.mark.parametrize(
    ("adapter", "document", "expected_name", "expected_degree"),
    [
        (
            BolognaAdapter(),
            """<div class="card-list-abstract"><div class="item">
            <div class="title"><h3>Data Science and Business Analytics</h3></div>
            <a href="https://www.unibo.it/en/study/second-cycle-degree/programme/2026/9999">Overview</a>
            </div></div>""",
            "Data Science and Business Analytics",
            "Master",
        ),
        (
            ChalmersAdapter(),
            json.dumps(
                {
                    "search": {
                        "results": [
                            {
                                "contentType": "ProgrammePageV2",
                                "title": "Data Science and AI, MSc",
                                "url": "/en/education/find-programmes/data-science-msc/",
                            },
                            {
                                "contentType": "Page",
                                "title": "Admissions",
                                "url": "/en/admissions/",
                            },
                        ]
                    }
                }
            ),
            "Data Science and AI, MSc",
            "MSc",
        ),
        (
            VUAmsterdamAdapter(),
            json.dumps(
                {
                    "value": [
                        {
                            "ItemType": ["All", "Study", "Master"],
                            "Title": "Artificial Intelligence",
                            "Url": "/en/education/master/artificial-intelligence",
                        },
                        {
                            "ItemType": [
                                "All",
                                "Study",
                                "Master",
                                "Specialization",
                            ],
                            "Title": "AI for Health",
                            "Url": "/en/education/master/ai-for-health",
                        },
                    ]
                }
            ),
            "Artificial Intelligence",
            "Master",
        ),
        (
            UCDAdapter(),
            json.dumps(
                {
                    "data": [
                        [
                            '<a class="crslink" href="!W_HU_MENU.P_PUBLISH?p_tag=COURSE&amp;MAJR=F123">Data Science</a>',
                            "F123",
                            "Graduate Taught",
                            "MSc",
                            "On Campus",
                            "FT",
                            "1 Year",
                            "CSC",
                            "GT",
                        ],
                        [
                            '<a class="crslink" href="/diploma">Data Science Diploma</a>',
                            "F124",
                            "Graduate Taught",
                            "GradDip",
                            "Online",
                            "PT",
                            "1 Year",
                            "CSC",
                            "GT",
                        ],
                    ]
                }
            ),
            "Data Science",
            "MSc",
        ),
        (
            KITAdapter(),
            """<main><div class="content"><div class="service-tile">
            <span class="headline">Data Science M.Sc.</span>
            <a href="/english/vorstudium/master-data-science.php">link</a>
            </div></div></main>""",
            "Data Science M.Sc.",
            "MSc",
        ),
    ],
)
def test_batch_three_official_catalogue_parsers(
    adapter, document, expected_name, expected_degree
) -> None:
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(document).programmes

    assert [programme.name for programme in programmes] == [expected_name]
    assert programmes[0].degree_type == expected_degree
    assert programmes[0].windows == []
    assert programmes[0].parse_status == "no-deadline"
    assert programmes[0].source_url.startswith("https://")


def test_vu_uses_search_api_first_and_parses_february_deadlines() -> None:
    api_payload = json.dumps(
        {
            "value": [
                {
                    "ItemType": ["Study", "Master"],
                    "ContentType": "programme_page",
                    "Title": "Mathematics",
                    "Url": "/en/education/master/mathematics",
                },
                {
                    "ItemType": ["Study", "Master"],
                    "ContentType": "programme_page",
                    "Title": "Law",
                    "Url": "/en/education/master/law",
                },
            ]
        }
    )
    fetched = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        if url == VU_APPLICATION_URL:
            return _vu_february_deadlines()
        raise AssertionError(url)

    catalog = VUAmsterdamAdapter(
        minimum_expected_programmes=2,
        search_api_fetcher=lambda: api_payload,
    ).parse_catalog_from_fetcher(fetcher)

    assert fetched == [VU_APPLICATION_URL]
    mathematics = next(
        item for item in catalog.programmes if item.name == "Mathematics"
    )
    law = next(item for item in catalog.programmes if item.name == "Law")
    assert [
        (item.applicant_categories, item.closes_at) for item in mathematics.windows
    ] == [
        (["eu-efta"], "2026-12-01"),
        (["non-eu-efta"], "2026-11-01"),
    ]
    assert [(item.applicant_categories, item.closes_at) for item in law.windows] == [
        (["eu-efta"], "2027-01-01"),
        (["non-eu-efta"], "2026-11-01"),
    ]
    assert all(
        window.opens_at is None
        for item in catalog.programmes
        for window in item.windows
    )


def test_vu_uses_static_catalogue_when_search_api_fails() -> None:
    wrapper = """
      <main><a href="/en/education/master/mathematics">Mathematics</a>
      <a href="/en/education/master/law">Law</a></main>
    """
    pages = {
        VU_CATALOG_URL: wrapper,
        VU_APPLICATION_URL: _vu_february_deadlines(),
    }

    def failed_api() -> str:
        raise RuntimeError("search unavailable")

    catalog = VUAmsterdamAdapter(
        minimum_expected_programmes=2,
        search_api_fetcher=failed_api,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert [item.name for item in catalog.programmes] == ["Law", "Mathematics"]
    assert catalog.warnings[0]["reason"] == "TRANSPORT_ERROR"
    assert catalog.warnings[0]["fallback"] == "official-static-catalogue"


def _vu_february_deadlines() -> str:
    return """
      <h4>Application deadlines</h4>
      <p>The application deadlines for international students wishing to start in February 2027 are as follows:</p>
      <ul><li>1 November 2026 for non-EU citizens/students who need a study visa.</li>
      <li>1 December 2026 for EU citizens for the Master programmes in Mathematics</li>
      <li>1 January 2027 for EU citizens for the Master in Law</li></ul>
      <h4>Start date: 1 February 2027</h4>
    """
