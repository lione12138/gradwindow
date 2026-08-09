from __future__ import annotations

import json

from gradwindow.programme_adapters.complutense import ComplutenseAdapter
from gradwindow.programme_adapters.curtin import CurtinAdapter
from gradwindow.programme_adapters.humboldt import HumboldtAdapter
from gradwindow.programme_adapters.iit_bombay import IITBombayAdapter
from gradwindow.programme_adapters.iit_madras import IITMadrasAdapter
from gradwindow.programme_adapters.kau import KAUAdapter
from gradwindow.programme_adapters.uchile import UChileAdapter
from gradwindow.programme_adapters.unam import UNAMAdapter
from gradwindow.programme_adapters.ustc import USTCAdapter
from gradwindow.programme_adapters.washu import WashUAdapter


def _small(adapter):
    adapter.minimum_expected_programmes = 1
    return adapter


def test_humboldt_extracts_master_routes_from_official_study_sitemap() -> None:
    programmes = (
        _small(HumboldtAdapter())
        .parse_catalog(
            """<?xml version="1.0"?><urlset>
        <url><loc>https://www.hu-berlin.de/studium/studienangebot/details/
        psychologie-master-of-science-hauptfach</loc></url>
        <url><loc>https://www.hu-berlin.de/studium/studienangebot/details/
        deutsch-bachelor-of-arts-kernfach</loc></url>
        <url><loc>https://www.hu-berlin.de/studium/studienangebot/details/
        englisch-master-of-education-isg-2-fach</loc></url>
        </urlset>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Englisch — Isg 2 Fach", "MEd"),
        ("Psychologie", "MSc"),
    ]


def test_kau_keeps_master_cards_and_rejects_bachelors() -> None:
    programmes = (
        _small(KAUAdapter())
        .parse_catalog(
            """<article><div class="mb-2 flex flex-wrap gap-2">
        <span>Advanced Studies - General Master</span></div>
        <h3>برنامج الماجستير في القانون الخاص</h3>
        <a href="/ar/programs/master-of-private-law">Details</a></article>
        <article><div class="mb-2 flex flex-wrap gap-2"><span>Bachelor</span></div>
        <h3>Bachelor of Accounting</h3>
        <a href="/ar/programs/accounting">Details</a></article>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("برنامج الماجستير في القانون الخاص", "Master")
    ]


def test_complutense_extracts_official_master_list_and_deduplicates() -> None:
    programmes = (
        _small(ComplutenseAdapter())
        .parse_catalog(
            """<h2>Artes y Humanidades</h2><ul class="menu_pag">
        <li><a href="/estudios/master-diseno">Diseño</a></li>
        <li><a href="/estudios/master-diseno">Diseño</a></li></ul>
        <h2>Grados</h2><ul><li><a href="/estudios/grado-diseno">Diseño</a></li></ul>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Diseño", "Máster")
    ]


def test_uchile_extracts_magister_links_only() -> None:
    programmes = (
        _small(UChileAdapter())
        .parse_catalog(
            """<h2>Facultad de Ciencias</h2><ul class="mod__list">
        <li><a class="mod__link" href="/postgrados/123/ciencia-de-datos">
        Magíster en Ciencia de Datos</a></li></ul>
        <a href="/doctorados/456/ciencias">Doctorado en Ciencias</a>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Magíster en Ciencia de Datos", "Magíster")
    ]


def test_uchile_reuses_existing_programme_id() -> None:
    programmes = (
        _small(UChileAdapter())
        .parse_catalog(
            """<a class="mod__link" href="/postgrados/123/computacion">
        Magíster en Ciencias, mención Computación</a>"""
        )
        .programmes
    )

    assert programmes[0].id == "uchile-magister-ciencias-computacion"


def test_unam_extracts_current_master_records_from_transparency_api() -> None:
    payload = {
        "status": "success",
        "records": [
            {
                "7226": "Coordinación de Ingeniería",
                "7227": "Maestría en Ingeniería",
                "7230": "Maestría",
                "7233": "https://www.posgrado.unam.mx/ingenieria/plan.pdf",
            },
            {
                "7226": "Coordinación de Ingeniería",
                "7227": "Doctorado en Ingeniería",
                "7230": "Doctorado",
                "7233": "https://www.posgrado.unam.mx/ingenieria/doctorado.pdf",
            },
        ],
    }
    programmes = _small(UNAMAdapter()).parse_catalog(json.dumps(payload)).programmes

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Maestría en Ingeniería", "Maestría")
    ]


def test_iit_bombay_expands_each_specialisation_in_official_tables() -> None:
    programmes = (
        _small(IITBombayAdapter())
        .parse_catalog(
            """<table><tr><td>Degree/Specialization</td><td>Department</td></tr>
        <tr><td><p>(AE1) Aerodynamics</p><p>(AE2) Dynamics &amp; Control</p></td>
        <td><a href="https://www.aero.iitb.ac.in/">Aerospace Engineering</a></td>
        </tr></table>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Aerodynamics", "M.Tech"),
        ("Dynamics & Control", "M.Tech"),
    ]


def test_iit_bombay_distinguishes_executive_mba() -> None:
    adapter = _small(IITBombayAdapter())
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(
        """<table></table><table></table><table></table><table>
        <tr><td>(EMBA) Master of Business Administration</td>
        <td><a href="https://www.som.iitb.ac.in/">SJMSOM</a></td></tr>
        </table>"""
    ).programmes

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Executive Master of Business Administration", "EMBA")
    ]


def test_iit_madras_tracks_department_for_mtech_ma_and_msc() -> None:
    programmes = (
        _small(IITMadrasAdapter())
        .parse_catalog(
            """<h2>M.Tech. Programmes Offered</h2><table><tbody>
        <tr class="department-row"><td><span class="dept-title">
        Department of Engineering Design</span></td></tr>
        <tr class="program-row"><td>M.Tech in Robotics <span>NEW</span></td></tr>
        </tbody></table><h2>M.Sc. Programmes Offered</h2><table>
        <tr><th>Department</th><th>Academic Programme [Code]</th></tr>
        <tr><td>Physics</td><td>Physics [1703]</td></tr></table>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("M.Tech in Robotics", "M.Tech"),
        ("Physics", "MSc"),
    ]


def test_iit_madras_reuses_existing_computer_science_id() -> None:
    programmes = (
        _small(IITMadrasAdapter())
        .parse_catalog(
            """<h2>M.Tech. Programmes Offered</h2><table><tbody>
        <tr class="program-row"><td>
        M.Tech in Computer Science and Engineering</td></tr></tbody></table>"""
        )
        .programmes
    )

    assert programmes[0].id == "iitm-mtech-computer-science-engineering"


def test_washu_filters_master_degree_pages_from_bulletin_index() -> None:
    programmes = (
        _small(WashUAdapter())
        .parse_catalog(
            """<a href="/grad/engineering/degrees/cse-computer-science-ms/">
        Computer Science, MS (CSE)</a>
        <a href="/grad/artsci/degrees/chemistry-phd/">Chemistry, PhD</a>
        <a href="/grad/business/graduate-masters/policies/">Policies</a>
        <a href="/grad/caps/m-data-analytics/">Data Analytics and Applications,
        School of Continuing &amp; Professional Studies, Graduate</a>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Computer Science, MS (CSE)", "MS"),
        ("Data Analytics and Applications", "Master"),
    ]
    assert programmes[0].id == "washu-computer-science-ms"


def test_ustc_carries_rowspanned_first_level_discipline() -> None:
    programmes = (
        _small(USTCAdapter())
        .parse_catalog(
            """<table><tr><th>First-level discipline</th>
        <th>Second-level discipline</th></tr>
        <tr><td rowspan="2">Mathematics</td><td>Fundamental Mathematics</td></tr>
        <tr><td>Applied Mathematics</td></tr></table>"""
        )
        .programmes
    )

    assert [item.name for item in programmes] == [
        "Mathematics: Applied Mathematics",
        "Mathematics: Fundamental Mathematics",
    ]


def test_curtin_keeps_master_course_pages_only() -> None:
    programmes = (
        _small(CurtinAdapter())
        .parse_catalog(
            """<h3><a href="/study/courses/master-of-artificial-intelligence/">
        Master of Artificial Intelligence</a></h3>
        <h3><a href="/study/courses/bachelor-of-science/">
        Bachelor of Science</a></h3>"""
        )
        .programmes
    )

    assert [(item.name, item.degree_type) for item in programmes] == [
        ("Master of Artificial Intelligence", "Master")
    ]
