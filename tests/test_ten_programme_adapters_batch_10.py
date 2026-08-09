from __future__ import annotations

import json

from gradwindow.programme_adapters.hokkaido import HokkaidoAdapter
from gradwindow.programme_adapters.postech import (
    APPLICATION_URL as POSTECH_APPLICATION_URL,
)
from gradwindow.programme_adapters.postech import CATALOG_URL as POSTECH_CATALOG_URL
from gradwindow.programme_adapters.postech import POSTECHAdapter
from gradwindow.programme_adapters.qmul import QMULAdapter
from gradwindow.programme_adapters.reading import ReadingAdapter
from gradwindow.programme_adapters.rwth import RWTHAdapter
from gradwindow.programme_adapters.sapienza import SapienzaAdapter
from gradwindow.programme_adapters.skku import SKKUAdapter
from gradwindow.programme_adapters.uow import UOWAdapter
from gradwindow.programme_adapters.upm import UPMAdapter
from gradwindow.programme_adapters.usm import USMAdapter


def test_qmul_extracts_coursefinder_api_records() -> None:
    adapter = QMULAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        json.dumps(
            {
                "response": {
                    "docs": [
                        {
                            "coursetitle": ["Accounting and Finance"],
                            "awardshortname": ["MSc"],
                            "coursepageurl": [
                                "https://www.qmul.ac.uk/postgraduate/taught/"
                                "coursefinder/courses/accounting-and-finance-msc/"
                            ],
                        }
                    ]
                }
            }
        )
    ).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Accounting and Finance", "MSc")
    ]


def test_rwth_keeps_only_master_rows() -> None:
    adapter = RWTHAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<table><tr><td>Course of Study
        <a class="iconless" href="/a">Applied Geography M.Sc.</a></td>
        <td>Degree Master</td></tr><tr><td>Course of Study
        <a class="iconless" href="/b">Applied Geography B.Sc.</a></td>
        <td>Degree Bachelor</td></tr></table>"""
    ).programmes

    assert [row.name for row in rows] == ["Applied Geography M.Sc."]


def test_postech_attaches_latest_exact_international_rounds() -> None:
    adapter = POSTECHAdapter()
    adapter.minimum_expected_programmes = 1
    pages = {
        POSTECH_CATALOG_URL: """<div class="select_form">ACADEMIC PROGRAM
        <a href="https://math.postech.ac.kr">MATHEMATICS</a></div>""",
        POSTECH_APPLICATION_URL: """<table>
        <tr><th>Year</th><th>Round</th><th>Name</th><th>Period</th></tr>
        <tr><td>2026-27</td><td>International Application - 2nd</td>
        <td>Graduate Admissions</td>
        <td>2026-07-06(MON)~2026-09-11(FRI)</td></tr>
        <tr><td>2025-26</td><td>International Application - 2nd</td>
        <td>Graduate Admissions</td>
        <td>2025-07-07(MON)~2025-09-12(FRI)</td></tr></table>""",
    }

    row = adapter.parse_catalog_from_fetcher(pages.__getitem__).programmes[0]

    assert row.parse_status == "exact"
    assert [(window.opens_at, window.closes_at) for window in row.windows] == [
        ("2026-07-06", "2026-09-11")
    ]


def test_skku_extracts_general_and_named_graduate_schools() -> None:
    adapter = SKKUAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter._catalog(
        adapter.extract_entries(
            """<div class="wel_txtcont"><h4>Engineering</h4>
            <h4>Graduate School of Governance</h4>
            <h4 class="popup-subtit">EMBA</h4></div>"""
        )
    ).programmes

    assert {row.name for row in rows} == {
        "Graduate Studies in Engineering",
        "Graduate School of Governance",
    }


def test_sapienza_keeps_second_cycle_lm_courses() -> None:
    adapter = SapienzaAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<ul><li class="corso-card"><div class="corso--header">
        <a href="/en/course/1">Data Science</a></div><div class="corso--infos">
        <div class="corso--tipologia">LM-Data</div></div></li>
        <li class="corso-card"><div class="corso--header">
        <a href="/en/course/2">Architecture</a></div><div class="corso--infos">
        <div class="corso--tipologia">LM-4 c.u.</div></div></li></ul>"""
    ).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Data Science", "Laurea Magistrale (LM-Data)")
    ]


def test_usm_extracts_official_master_links() -> None:
    adapter = USMAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<a href="/index.php/pure-sciences/msc-biology">MSc (Biology)</a>
        <a href="/undergraduate/biology">BSc Biology</a>"""
    ).programmes

    assert [row.name for row in rows] == ["MSc (Biology)"]


def test_upm_follows_coursework_faculties_and_extracts_master_names() -> None:
    adapter = UPMAdapter()
    adapter.minimum_expected_programmes = 1
    pages = {
        adapter.catalog_url: (
            '<a href="/programme_of_study/programme_by_coursework/'
            'faculty_of_science-1425">Faculty of Science</a>'
        ),
        "https://sgs.upm.edu.my/programme_of_study/"
        "programme_by_coursework/faculty_of_science-1425": (
            "<strong>Master of Science</strong><strong>Coordinator</strong>"
        ),
        adapter.application_url: "Applications",
    }

    rows = adapter.parse_catalog_from_fetcher(pages.__getitem__).programmes

    assert [row.name for row in rows] == ["Master of Science"]


def test_hokkaido_excludes_doctoral_only_english_programme() -> None:
    adapter = HokkaidoAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<h3 id="study-in-english">Study in English</h3><p>Programs</p><ul>
        <li><a href="/agriscience">Agriscience</a></li>
        <li><a href="/one-health">One Health (Doctoral Program)</a></li>
        </ul><h3 id="study-in-japanese">Study in Japanese</h3>"""
    ).programmes

    assert [row.name for row in rows] == ["Agriscience"]


def test_uow_extracts_master_courses_from_official_search_payload() -> None:
    adapter = UOWAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        json.dumps(
            {
                "result": [
                    {
                        "coursetitle": "Master of Public Health",
                        "url": "https://www.uow.edu.au/study/courses/"
                        "master-of-public-health/",
                    },
                    {
                        "coursetitle": "Bachelor of Health",
                        "url": "https://www.uow.edu.au/study/courses/bachelor-health/",
                    },
                ]
            }
        )
    ).programmes

    assert [row.name for row in rows] == ["Master of Public Health"]


def test_reading_discovers_subject_pages_and_master_course_links() -> None:
    adapter = ReadingAdapter()
    adapter.minimum_expected_programmes = 1
    subject_url = (
        "https://www.reading.ac.uk/ready-to-study/study/2026/computer-science-pg"
    )
    pages = {
        adapter.catalog_url: f'<a href="{subject_url}">Computer Science</a>',
        subject_url: f'<a href="{subject_url}/msc-data-science">MSc Data Science</a>',
        adapter.application_url: "Applications",
    }

    rows = adapter.parse_catalog_from_fetcher(pages.__getitem__).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("MSc Data Science", "MSc")
    ]
