from __future__ import annotations

import pytest

from gradwindow.programme_adapters.aalto import AaltoAdapter
from gradwindow.programme_adapters.basel import BaselAdapter
from gradwindow.programme_adapters.bath import BathAdapter
from gradwindow.programme_adapters.boston import BostonAdapter
from gradwindow.programme_adapters.dtu import DTUAdapter
from gradwindow.programme_adapters.exeter import ExeterAdapter
from gradwindow.programme_adapters.fu_berlin import FUBerlinAdapter
from gradwindow.programme_adapters.groningen import GroningenAdapter
from gradwindow.programme_adapters.helsinki import HelsinkiAdapter
from gradwindow.programme_adapters.leiden import LeidenAdapter
from gradwindow.programme_adapters.liverpool import LiverpoolAdapter
from gradwindow.programme_adapters.newcastle import NewcastleAdapter
from gradwindow.programme_adapters.oslo import OsloAdapter
from gradwindow.programme_adapters.rice import RiceAdapter
from gradwindow.programme_adapters.rmit import RMITAdapter
from gradwindow.programme_adapters.uzh import UZHAdapter
from gradwindow.programme_adapters.vienna import ViennaAdapter
from gradwindow.programme_adapters.wageningen import WageningenAdapter
from gradwindow.programme_adapters.waterloo import WaterlooAdapter
from gradwindow.programme_adapters.york import YorkAdapter


@pytest.mark.parametrize(
    ("adapter", "document", "expected_name"),
    [
        (
            BostonAdapter(),
            '<li class="ma">Computer Science (<a href="/academics/cas/cs/ms/">MS</a>)</li>',
            "Computer Science (MS)",
        ),
        (
            FUBerlinAdapter(),
            '<a href="/studium/studienangebot/master/data_science/index.html">Data Science</a>',
            "Data Science",
        ),
        (
            UZHAdapter(),
            '<a href="/de/studies/programs/master/data_science.html">Data Science</a>',
            "Data Science",
        ),
        (
            WaterlooAdapter(),
            '<a href="/future-graduate-students/programs/by-faculty/math/data-science-master">Data Science - Master of Data Science</a>',
            "Data Science - Master of Data Science",
        ),
        (
            BathAdapter(),
            '<a href="/courses/postgraduate-2026/taught-postgraduate-courses/data-science-msc/">Data Science MSc – 1 year</a>',
            "Data Science MSc",
        ),
        (
            DTUAdapter(),
            '<a href="/english/education/graduate/msc-programmes/computer-science-and-engineering">Course</a>',
            "MSc Computer Science And Engineering",
        ),
        (
            ExeterAdapter(),
            '<a href="/masters-degrees/msc-data-science/">MSc Data Science</a>',
            "MSc Data Science",
        ),
        (
            LiverpoolAdapter(),
            '<a href="/courses/data-science-and-ai-msc">Data Science and AI</a>',
            "Data Science and AI (MSC)",
        ),
        (
            YorkAdapter(),
            '<a href="/study/postgraduate-taught/courses/msc-data-science/">Data Science</a>',
            "Data Science (MSC)",
        ),
        (
            NewcastleAdapter(),
            '<a href="/postgraduate/degrees/1234f/">Data Science MSc</a>',
            "Data Science MSc",
        ),
        (
            LeidenAdapter(),
            '<a href="/en/education/study-programmes/master/data-science">Master Data Science (MSc)</a>',
            "Data Science (MSc)",
        ),
        (
            RiceAdapter(),
            '<table><tr><td><a href="/programs/data-science/">Master of Data Science (MDS) Degree</a></td></tr></table>',
            "Master of Data Science (MDS) Degree",
        ),
        (
            OsloAdapter(),
            '<a href="https://www.uio.no/english/studies/programmes/data-science-master/">Data Science (master)</a>',
            "Data Science",
        ),
        (
            ViennaAdapter(),
            '<a href="/en/degree-programmes/master-programmes/data-science-master/">Data Science (Master)</a>',
            "Data Science",
        ),
        (
            GroningenAdapter(),
            '<a href="/masters/data-science/">Data Science</a>',
            "Data Science",
        ),
        (
            BaselAdapter(),
            '<a class="newsbox_listing_link" href="/degree?study=Data&amp;degree=master"><span>Data Science</span><span>Master</span></a>',
            "Data Science",
        ),
    ],
)
def test_official_html_catalogue_parsers(adapter, document, expected_name) -> None:
    adapter.minimum_expected_programmes = 1
    catalog = adapter.parse_catalog(document)

    assert [programme.name for programme in catalog.programmes] == [expected_name]
    programme = catalog.programmes[0]
    assert programme.windows == []
    assert programme.parse_status == "no-deadline"
    assert programme.evidence_quality == "official-full-text"


@pytest.mark.parametrize(
    ("adapter", "location", "expected_name"),
    [
        (
            RMITAdapter(),
            "https://www.rmit.edu.au/study-with-us/levels-of-study/postgraduate-study/masters-by-coursework/master-of-data-science-mc267",
            "Master Of Data Science",
        ),
        (
            AaltoAdapter(),
            "https://www.aalto.fi/en/study-options/data-science-master-of-science-technology",
            "Data Science",
        ),
        (
            HelsinkiAdapter(),
            "https://www.helsinki.fi/en/degree-programmes/data-science-masters-programme",
            "Master's Programme in Data Science",
        ),
    ],
)
def test_official_sitemap_catalogue_parsers(adapter, location, expected_name) -> None:
    adapter.minimum_expected_programmes = 1
    document = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{location}</loc></url></urlset>'

    assert adapter.parse_catalog(document).programmes[0].name == expected_name


def test_wageningen_embedded_official_catalogue_parser() -> None:
    adapter = WageningenAdapter()
    adapter.minimum_expected_programmes = 1
    document = r"\"id\":123,\"title\":\"Master’s in Data Science\",\"path\":\"/en/education/master/masters-data-science\""

    assert (
        adapter.parse_catalog(document).programmes[0].name == "Master’s in Data Science"
    )
