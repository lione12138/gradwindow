from __future__ import annotations

import json

from gradwindow.programme_adapters.hit import HITAdapter
from gradwindow.programme_adapters.ncku import NCKUAdapter
from gradwindow.programme_adapters.tec_monterrey import TecMonterreyAdapter
from gradwindow.programme_adapters.uclouvain import UCLouvainAdapter
from gradwindow.programme_adapters.universitas_indonesia import (
    UniversitasIndonesiaAdapter,
)


def test_tec_monterrey_reads_only_official_masters_links() -> None:
    html = """
      <a class="link-program" href="/posgrados/maestria-en-ciencia-de-datos">
        Maestría en Ciencia de Datos (MCD)
      </a>
      <a class="link-program" href="/posgrados/maestria-en-finanzas">
        Maestría en Finanzas (MAF)
      </a>
      <a class="link-program" href="/posgrados/doctorado-en-finanzas">
        Doctorado en Finanzas (DCF)
      </a>
    """
    rows = (
        TecMonterreyAdapter(minimum_expected_programmes=2)
        .parse_catalog(html)
        .programmes
    )
    assert [row.name for row in rows] == [
        "Maestría en Ciencia de Datos (MCD)",
        "Maestría en Finanzas (MAF)",
    ]
    assert all(row.windows == [] for row in rows)


def test_hit_reads_chinese_and_english_taught_xlsx_catalogues() -> None:
    page = """
      <a href="/files/chinese.xlsx">
        Master's Degree Programs (Chinese-taught)-Major List.xlsx
      </a>
      <a href="/files/english.xlsx">
        Master's Degree Programs (English-taught)-Major List.xlsx
      </a>
    """
    sheets = {
        "https://studyathit.hit.edu.cn/files/chinese.xlsx": _hit_sheet(
            "Chinese", "社会学\nSociology", "人文社科学部\nFaculty of Humanities"
        ),
        "https://studyathit.hit.edu.cn/files/english.xlsx": _hit_sheet(
            "English",
            "计算机科学与技术\nComputer Science and Technology",
            "计算学部\nFaculty of Computing",
        ),
    }
    rows = (
        HITAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(
            lambda url: page if url == HITAdapter.catalog_url else sheets[url]
        )
        .programmes
    )
    assert [row.name for row in rows] == [
        "Computer Science and Technology (English-taught)",
        "Sociology (Chinese-taught)",
    ]
    assert {row.faculty for row in rows} == {
        "Faculty of Computing",
        "Faculty of Humanities",
    }


def test_ncku_reads_master_routes_and_one_shared_exact_window() -> None:
    catalog = """
      <table>
        <tr><td>Graduate</td></tr>
        <tr><td>College of Engineering</td></tr>
        <tr><td>[M] Department of Civil Engineering</td><td>link</td></tr>
        <tr><td>[M] [D] Department of Mechanical Engineering</td><td>link</td></tr>
      </table>
    """
    admissions = (
        "Spring 2027 Application for International Degree Students "
        "Application period: July 1, 2026 (Wed) to September 15 (Tue) 2026"
    )
    pages = {
        NCKUAdapter.catalog_url: catalog,
        NCKUAdapter.admissions_url: admissions,
    }
    rows = (
        NCKUAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )
    assert [row.name for row in rows] == [
        "Department of Civil Engineering",
        "Department of Mechanical Engineering",
        "International degree programmes",
    ]
    assert rows[0].windows == []
    assert rows[-1].windows[0].opens_at == "2026-07-01"
    assert rows[-1].windows[0].closes_at == "2026-09-15"


def test_universitas_indonesia_reads_s2_requirements_archive() -> None:
    html = """
      <h1>Penerimaan S2 Jalur SIMAK</h1>
      <table>
        <tr><th>Program Studi</th><th>Persyaratan</th></tr>
        <tr><td>Teknik</td></tr>
        <tr><td>Teknik Sipil</td><td>Requirements</td></tr>
        <tr><td>Ilmu Komputer</td></tr>
        <tr><td>Ilmu Komputer</td><td>Requirements</td></tr>
      </table>
    """
    rows = (
        UniversitasIndonesiaAdapter(minimum_expected_programmes=2)
        .parse_catalog(html)
        .programmes
    )
    assert [row.name for row in rows] == ["Ilmu Komputer", "Teknik Sipil"]
    assert rows[0].id == "ui-magister-ilmu-komputer"
    assert all(row.parse_status == "no-deadline" for row in rows)


def test_uclouvain_reads_current_master_catalogue() -> None:
    html = """
      <a href="/prog-2026-info2m">Master [120] : ingénieur civil en informatique
        (Louvain-la-Neuve)</a>
      <a href="/prog-2026-math2m1">Master [60] en sciences mathématiques
        (Louvain-la-Neuve)</a>
      <a href="/prog-2026-biol1ba">Bachelier en sciences biologiques</a>
    """
    rows = (
        UCLouvainAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes
    )
    assert [row.degree_type for row in rows] == ["Master 120", "Master 60"]
    assert all("prog-2026-" in row.source_url for row in rows)


def _hit_sheet(language: str, programme: str, faculty: str) -> str:
    return json.dumps(
        {
            "worksheets": [
                {
                    "name": "Sheet1",
                    "rows": [
                        ["Master's Degree Programs", None, None, None],
                        ["No.", "School", "Major", "Teaching Language"],
                        [1, faculty, programme, language],
                    ],
                }
            ]
        }
    )
