from __future__ import annotations

import json

from gradwindow.programme_adapters.geneva import (
    APPLICATION_URL as GENEVA_APPLICATION_URL,
)
from gradwindow.programme_adapters.geneva import (
    CATALOG_URL as GENEVA_CATALOG_URL,
)
from gradwindow.programme_adapters.geneva import CATEGORY_URL, GenevaAdapter
from gradwindow.programme_adapters.kyushu import KyushuAdapter
from gradwindow.programme_adapters.nagoya import NagoyaAdapter
from gradwindow.programme_adapters.nthu import (
    ADMISSIONS_INDEX_URL,
    NTHUAdapter,
    _application_window,
    _degree_entries,
    _latest_admission_url,
)
from gradwindow.programme_adapters.queens_ontario import QueensOntarioAdapter


def test_queens_expands_masters_degrees_and_filters_joint_degrees() -> None:
    adapter = QueensOntarioAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<h3>Faculty of Arts and Science</h3><table>
        <tr><td><a href="/computing">Computing</a></td>
        <td>M.Sc., MA/JD, PhD, MEng (professional)</td></tr>
        </table>"""
    ).programmes

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Computing", "MEng"),
        ("Computing", "MSc"),
    ]
    assert all(item.faculty == "Faculty of Arts and Science" for item in programmes)


def test_geneva_uses_master_category_and_faculty_metadata() -> None:
    adapter = GenevaAdapter()
    adapter.minimum_expected_programmes = 1
    cards = json.dumps(
        [
            {
                "id": 540,
                "name": "Classical Archaeology",
                "categories": [273, 156],
                "path": (
                    "https://www.unige.ch/bachelor-master/en/masters/"
                    "classical-archaeology"
                ),
            },
            {
                "id": 999,
                "name": "Bachelor only",
                "categories": [272, 156],
                "path": "https://www.unige.ch/bachelor",
            },
        ]
    )
    categories = json.dumps(
        [
            {
                "title": "Faculty / Institute / Center",
                "values": [{"id": 156, "text": "Humanities"}],
            }
        ]
    )
    fetched = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        return {
            GENEVA_CATALOG_URL: cards,
            CATEGORY_URL: categories,
            GENEVA_APPLICATION_URL: "Official enrollment conditions",
        }[url]

    programme = adapter.parse_catalog_from_fetcher(fetcher).programmes[0]

    assert programme.id == "geneva-master-540"
    assert programme.faculty == "Humanities"
    assert fetched == [GENEVA_CATALOG_URL, CATEGORY_URL, GENEVA_APPLICATION_URL]


def test_kyushu_carries_rowspanned_faculty_and_filters_doctoral_only() -> None:
    adapter = KyushuAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table class="p-list__table">
        <tr><td><a href="school/">Graduate School of Science</a></td>
        <td>International Master's/Doctoral Program in Science</td><td>M/D</td></tr>
        <tr><td>International Doctoral Program</td><td>D</td></tr>
        <tr><td>Applied Science Master's Program</td><td>M</td></tr>
        </table>"""
    ).programmes

    assert len(programmes) == 2
    assert all(item.faculty == "Graduate School of Science" for item in programmes)


def test_nagoya_requires_mark_in_masters_column() -> None:
    adapter = NagoyaAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table>
        <tr><td><a href="/masters">Economics</a></td><td>Economics</td>
        <td><img src="master.png"></td><td></td></tr>
        <tr><td><a href="/doctoral">Medical Science</a></td><td>Medicine</td>
        <td></td><td><img src="doctor.png"></td></tr>
        </table>"""
    ).programmes

    assert [item.name for item in programmes] == ["Economics"]


def test_nthu_parses_wrapped_pdf_entries_and_exact_shared_scope() -> None:
    assert _degree_entries(
        """Department of Mathematics Master of Science
        Institute of Technology Management Master of Business Administration in
        Technology Management
        International Intercollegiate Master Program"""
    ) == [
        ("Department of Mathematics", "Master of Science"),
        (
            "Institute of Technology Management",
            "Master of Business Administration in Technology Management",
        ),
        ("International Intercollegiate Master Program", "Master"),
    ]

    index = """<div class="card-body">
    <div>Spring 2027 Admission for International Degree Programs</div>
    <div>Application Period: August 3, 2026 – September 30, 2026</div>
    <a href="/en/article/210-admission"></a></div>"""
    article_url = _latest_admission_url(index)
    assert article_url == "https://apply.nthu.edu.tw/en/article/210-admission"
    window = _application_window(
        """<h1>Spring 2027 Admission for International Degree Programs</h1>
        <p>Application Period: August 3, 2026 – September 30, 2026</p>""",
        article_url,
    )
    adapter = NTHUAdapter()
    adapter.minimum_expected_programmes = 1
    catalog = adapter.parse_catalog(
        "Department of Mathematics Master of Science",
        window,
    )
    scope = next(
        item
        for item in catalog.programmes
        if item.id == "nthu-international-graduate-admissions"
    )

    assert catalog.application_opens_at == "2026-08-03"
    assert scope.windows[0].closes_at == "2026-09-30"
    assert scope.windows[0].applicant_categories == ["international-students"]
    assert ADMISSIONS_INDEX_URL == scope.application_url
