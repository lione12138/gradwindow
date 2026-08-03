from __future__ import annotations

import json

import pytest

from gradwindow.programme_adapters.copenhagen import CopenhagenAdapter
from gradwindow.programme_adapters.ghent import GhentAdapter
from gradwindow.programme_adapters.st_andrews import StAndrewsAdapter
from gradwindow.programme_adapters.stockholm import StockholmAdapter
from gradwindow.programme_adapters.tu_wien import TUWienAdapter


@pytest.mark.parametrize(
    ("adapter", "document", "expected_name"),
    [
        (
            CopenhagenAdapter(),
            json.dumps(
                {
                    "studyProgrammes": (
                        '<article data-study-programme="1">'
                        '<a href="/studies/masters/data-science">Data Science</a>'
                        "</article>"
                    )
                }
            ),
            "Data Science",
        ),
        (
            GhentAdapter(),
            """\
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://studiekiezer.ugent.be/master-of-science-in-data-science-en</loc></url>
<url><loc>https://studiekiezer.ugent.be/master-of-science-in-de-datawetenschappen</loc></url></urlset>
""",
            "Master of Science in Data Science",
        ),
        (
            TUWienAdapter(),
            """\
<main><a href="/en/studies/studies/master-programmes/data-science">Master's Programme Data Science</a>
<a href="https://example.org/external">Master's Programme External</a></main>
""",
            "Data Science",
        ),
        (
            StAndrewsAdapter(),
            '<a class="search-result__link" href="https://www.st-andrews.ac.uk/subjects/data-science/">Data Science (MSc)</a>',
            "Data Science (MSc)",
        ),
    ],
)
def test_official_catalogue_parsers(adapter, document, expected_name) -> None:
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(document).programmes

    assert [programme.name for programme in programmes] == [expected_name]
    assert programmes[0].windows == []
    assert programmes[0].parse_status == "no-deadline"
    assert programmes[0].source_url.startswith("https://")


def test_stockholm_parser_keeps_only_master_programmes() -> None:
    adapter = StockholmAdapter()
    adapter.minimum_expected_programmes = 1
    payload = json.dumps(
        [
            {
                "name": "Master's Programme in Data Science",
                "educationType": "Programme",
                "uri": "/english/education/course-catalogue/data-science",
            },
            {
                "name": "Bridging Teacher Education Programme",
                "educationType": "Programme",
                "uri": "/english/education/course-catalogue/teacher",
            },
            {
                "name": "Master's Programme in Biology, Molecular Life Sciences",
                "educationType": "Specialisation",
                "uri": "/english/education/course-catalogue/biology-molecular-life-sciences",
            },
            {
                "name": "Master's Thesis in Data Science",
                "educationType": "Course",
                "uri": "/english/education/course-catalogue/thesis",
            },
        ]
    )

    programmes = adapter.parse_catalog(payload).programmes

    assert [programme.name for programme in programmes] == [
        "Master's Programme in Biology, Molecular Life Sciences",
        "Master's Programme in Data Science",
    ]
