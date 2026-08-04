from __future__ import annotations

import json

import pytest

from gradwindow.programme_adapters.bern import BernAdapter
from gradwindow.programme_adapters.erasmus import ErasmusAdapter
from gradwindow.programme_adapters.purdue import PurdueAdapter
from gradwindow.programme_adapters.tu_berlin import TUBerlinAdapter
from gradwindow.programme_adapters.uppsala import UppsalaAdapter


@pytest.mark.parametrize(
    ("adapter", "document", "expected_name", "expected_degree"),
    [
        (
            UppsalaAdapter(),
            json.dumps(
                [
                    {
                        "title": "Master's Programme in Data Science, "
                        "120&nbsp;credits (TDS2M)",
                        "uri": "/en/study/programme/masters-programme-data-science",
                    }
                ]
            ),
            "Master's Programme in Data Science, 120 credits (TDS2M)",
            "Master",
        ),
        (
            TUBerlinAdapter(),
            """<a href="/en/studying/study-programs/all-programs-offered/study-course/computer-science-m-sc">
            <h2 class="studypaths__listItemName">Computer Science (M.Sc.)</h2>
            </a>""",
            "Computer Science (M.Sc.)",
            "MSc",
        ),
        (
            ErasmusAdapter(),
            """<article class="teaser teaser--linked">
            <h2 class="teaser__title"><a href="/en/master/data-science">
            Data Science and Marketing Analytics</a></h2>
            <ul><li>Master</li><li>English</li></ul></article>""",
            "Data Science and Marketing Analytics",
            "Master",
        ),
        (
            BernAdapter(),
            """<h2>Mono/major study programs from A to Z</h2>
            <div><ul class="nav-list"><li>
            <a href="https://www.philnat.unibe.ch/data-science">
            Data Science (Mono, Major)</a></li></ul></div>""",
            "Data Science",
            "Master",
        ),
        (
            PurdueAdapter(),
            """<div class="program-card"
            data-category="residential masters west-lafayette-indianapolis">
            <h2>Computer Science</h2>
            <p class="degree_level-label">Doctoral, Masters</p>
            <a href="https://www.purdue.edu/academics/ogsps/admissions/gradrequirements/westlafayette/computer-science/">
            Admission Requirements</a></div>
            <div class="program-card"
            data-category="residential masters purdue-fort-wayne">
            <h2>Computer Science (PFW)</h2>
            <p class="degree_level-label">Masters</p>
            <a href="https://www.purdue.edu/academics/ogsps/admissions/gradrequirements/fortwayne/computer-science/">
            Admission Requirements</a></div>""",
            "Computer Science",
            "Master",
        ),
    ],
)
def test_batch_four_official_catalogue_parsers(
    adapter, document, expected_name, expected_degree
) -> None:
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(document).programmes

    assert [programme.name for programme in programmes] == [expected_name]
    assert programmes[0].degree_type == expected_degree
    assert programmes[0].windows == []
    assert programmes[0].parse_status == "no-deadline"
    assert programmes[0].source_url.startswith("https://")


def test_erasmus_preserves_existing_curated_programme_id() -> None:
    adapter = ErasmusAdapter()
    adapter.minimum_expected_programmes = 1

    programmes = adapter.parse_catalog(
        """<article class="teaser teaser--linked">
        <h2 class="teaser__title">
        <a href="/en/master/data-science-and-marketing-analytics">
        Data Science and Marketing Analytics</a></h2></article>"""
    ).programmes

    assert [programme.id for programme in programmes] == [
        "erasmus-data-science-marketing-analytics"
    ]
