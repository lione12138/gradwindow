from __future__ import annotations

from gradwindow.programme_adapters.cmu import CMUAdapter
from gradwindow.programme_adapters.michigan import MichiganAdapter
from gradwindow.programme_adapters.nyu import NYUAdapter
from gradwindow.programme_adapters.trinity import TrinityAdapter
from gradwindow.programme_adapters.uba import UBAAdapter


def test_michigan_extracts_non_rackham_masters_by_faculty() -> None:
    adapter = MichiganAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """Other Graduate Degree Programs
        Ross School of Business
        • Master of Business Administration (M.B.A.)
        • Doctor of Philosophy (Ph.D.)
        School of Information
        • Master of Applied Data Science (M.A.D.S.)
        Professional Degree Programs"""
    ).programmes

    assert {(item.name, item.faculty) for item in rows} == {
        ("Master of Business Administration (M.B.A.)", "Ross School of Business"),
        ("Master of Applied Data Science (M.A.D.S.)", "School of Information"),
    }


def test_nyu_keeps_graduate_masters_cards() -> None:
    adapter = NYUAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<ul><li class="item"><a href="/graduate/engineering/programs/cs-ms/">
        <div class="item-container"><span class="title">Computer Science (MS)</span>
        <span class="keyword">MS</span><span class="keyword">Masters</span>
        <span class="keyword">Graduate</span><span class="keyword">Tandon</span>
        </div></a></li><li class="item"><a href="/undergraduate/cs-bs/">
        <div class="item-container"><span class="title">Computer Science (BS)</span>
        <span class="keyword">BS</span><span class="keyword">Bachelors</span>
        <span class="keyword">Undergraduate</span></div></a></li></ul>"""
    ).programmes

    assert [(item.name, item.degree_type, item.faculty) for item in rows] == [
        ("Computer Science (MS)", "MS", "Tandon")
    ]


def test_cmu_uses_explicit_materials_ms_links_only() -> None:
    adapter = CMUAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<h2>The department offers the following master of science degrees:</h2>
        <ul><li><a href="ms-materials.html">MS in Materials Science</a></li>
        <li>Dual Degree with<ul><li><a href="dual.html">Engineering Management</a>
        </li></ul></li></ul>"""
    ).programmes

    assert [item.name for item in rows] == ["MS in Materials Science"]


def test_trinity_extracts_taught_and_research_msc_routes() -> None:
    adapter = TrinityAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<h2>M.Sc. in High-Performance Computing</h2>
        <p>One year.</p><a href="./masters/">Read More</a>
        <h2>M.Sc. and Ph.D. by research</h2>
        <p>Research.</p><a href="./research/">Read More</a>"""
    ).programmes

    assert {item.name for item in rows} == {
        "M.Sc. in High-Performance Computing",
        "Mathematics by Research (M.Sc.)",
    }


def test_uba_extracts_exactas_maestria_cards() -> None:
    adapter = UBAAdapter()
    adapter.minimum_expected_programmes = 1
    rows = adapter.parse_catalog(
        """<a href="https://ambientales.at.fcen.uba.ar/">
        <h2 class="titulo">Maestría en Ciencias Ambientales</h2></a>
        <h2 class="titulo">Otras Carreras</h2>"""
    ).programmes

    assert [(item.name, item.degree_type) for item in rows] == [
        ("Maestría en Ciencias Ambientales", "Maestría")
    ]
