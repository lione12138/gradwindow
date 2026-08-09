from __future__ import annotations

from gradwindow.programme_adapters.iit_delhi import IITDelhiAdapter
from gradwindow.programme_adapters.macquarie import MacquarieAdapter
from gradwindow.programme_adapters.puc_chile import PUCChileAdapter
from gradwindow.programme_adapters.ukm import UKMAdapter
from gradwindow.programme_adapters.usp import USPAdapter


def test_iit_delhi_tracks_current_pg_admissions_brochure() -> None:
    rows = (
        IITDelhiAdapter()
        .parse_catalog(
            """
        <h1>PG ADMISSIONS : IIT Delhi</h1>
        <a href="https://ecampus.iitd.ac.in/PGADM/">Ph.D. and PG Programmes admission</a>
        <a>Information Brochure for Ph.D. and PG Admissions for 1st Semester 2026-27</a>
        """
        )
        .programmes
    )
    assert [(row.name, row.parse_status) for row in rows] == [
        ("Postgraduate programmes", "no-deadline")
    ]


def test_puc_chile_crawls_all_magister_archive_pages() -> None:
    adapter = PUCChileAdapter(minimum_expected_programmes=2)
    first = """
      <a href="/postgrado/magister/magister-en-arquitectura/">Magíster en Arquitectura</a>
      <a href="/postgrado/magister/page/2/">2</a>
    """
    second = """
      <a href="/postgrado/magister/magister-en-historia/">Magíster en Historia</a>
      <a href="/postgrado/magister/magister-en-historia/">Ver magíster</a>
    """
    rows = adapter.parse_catalog_from_fetcher(
        lambda url: second if url.endswith("/page/2/") else first
    ).programmes
    assert [row.name for row in rows] == [
        "Magíster en Arquitectura",
        "Magíster en Historia",
    ]


def test_macquarie_monitors_current_official_handbook_sitemap() -> None:
    rows = (
        MacquarieAdapter()
        .parse_catalog(
            """<sitemapindex>
        <sitemap><loc>https://coursehandbook.mq.edu.au/sitemap/sitemap-1.xml</loc>
        <lastmod>2026-07-08</lastmod></sitemap>
        </sitemapindex>"""
        )
        .programmes
    )
    assert rows[0].name == "2026 course handbook catalogue"


def test_ukm_expands_degree_headings_into_named_programmes() -> None:
    adapter = UKMAdapter(minimum_expected_programmes=2)
    index = '<a href="/studyukm/master-engineering/">Master</a>'
    detail = """
      <a class="elementor-toggle-title">Programme</a>
      <div class="elementor-tab-content">
        <p><strong>Master of Science</strong></p>
        <p>Mechanical Engineering</p>
        <p>Manufacturing Engineering</p>
        <p>Mode of Study: Research</p>
        <p>A. Mode of Study: Research Only</p>
        <p>REQUIREMENTS FOR ADMISSION TO THE PROGRAMMES</p>
      </div>
    """
    rows = adapter.parse_catalog_from_fetcher(
        lambda url: index if url == adapter.catalog_url else detail
    ).programmes
    assert [row.name for row in rows] == [
        "Master of Science in Manufacturing Engineering",
        "Master of Science in Mechanical Engineering",
    ]


def test_usp_extracts_official_graduate_programme_table() -> None:
    adapter = USPAdapter(minimum_expected_programmes=2)
    rows = adapter.parse_catalog(
        """<table><tr><th>Nome do programa</th><th>e-mail do programa</th></tr>
        <tr><td>Administração</td><td>admin@usp.br</td></tr>
        <tr><td>Bioinformática</td><td>bio@usp.br</td></tr></table>"""
    ).programmes
    assert [row.name for row in rows] == ["Administração", "Bioinformática"]
    assert all(row.degree_type == "Graduate programme" for row in rows)
