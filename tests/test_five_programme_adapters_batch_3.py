from __future__ import annotations

import json

import pytest

from gradwindow.programme_adapters.bologna import BolognaAdapter
from gradwindow.programme_adapters.chalmers import ChalmersAdapter
from gradwindow.programme_adapters.kit import KITAdapter
from gradwindow.programme_adapters.ucd import UCDAdapter
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
