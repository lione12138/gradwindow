from __future__ import annotations

import json

from gradwindow.programme_adapters.alberta import AlbertaAdapter
from gradwindow.programme_adapters.durham import DurhamAdapter
from gradwindow.programme_adapters.ksu import KSUAdapter
from gradwindow.programme_adapters.msu import MSUAdapter
from gradwindow.programme_adapters.utrecht import UtrechtAdapter


def test_durham_crawls_current_postgraduate_handbook_departments() -> None:
    adapter = DurhamAdapter(minimum_expected_programmes=2)
    department_url = f"{adapter.catalog_url}/department/Engineering"

    def fetcher(url: str) -> str:
        if url == adapter.catalog_url:
            return '<a href="/faculty.handbook/2026/PG/department/Engineering">Engineering</a>'
        assert url == department_url
        return """
        <a href="/faculty.handbook/2026/PG/programme/H1K209">
          H1K209: MSc Advanced Mechanical Engineering
        </a>
        <a href="/faculty.handbook/2026/PG/programme/H1K214">
          H1K214: Postgraduate Certificate Engineering
        </a>
        <a href="/faculty.handbook/2026/PG/programme/H1K215">
          H1K215: Master of Engineering Management
        </a>
        """

    rows = adapter.parse_catalog_from_fetcher(fetcher).programmes
    assert [(row.name, row.degree_type) for row in rows] == [
        ("Master of Engineering Management", "Master"),
        ("MSc Advanced Mechanical Engineering", "MSc"),
    ]


def test_alberta_monitors_current_official_calendar_when_directory_is_blocked() -> None:
    adapter = AlbertaAdapter()
    rows = adapter.parse_catalog(
        """
        <span class="acalog_catalog_name">University of Alberta Calendar 2026-2027</span>
        <a href="/content.php?catoid=69&amp;navoid=20894">Graduate Programs</a>
        """
    ).programmes
    assert [(row.name, row.parse_status) for row in rows] == [
        ("Graduate programs catalogue", "no-deadline")
    ]


def test_ksu_extracts_master_programme_cells_only() -> None:
    adapter = KSUAdapter(minimum_expected_programmes=2)
    rows = adapter.parse_catalog(
        """
        <table><tr><td>Arts</td><td>Master of Arts in History</td></tr>
        <tr><td>Literature and Criticism</td></tr>
        <tr><td>Master of Law (Public Law)</td></tr>
        <tr><td>Doctor of Philosophy in History</td></tr></table>
        """
    ).programmes
    assert [row.name for row in rows] == [
        "Master of Arts in History",
        "Master of Law (Public Law)",
    ]


def test_utrecht_uses_only_root_master_programme_urls_from_sitemaps() -> None:
    adapter = UtrechtAdapter(minimum_expected_programmes=2)
    index = """<sitemapindex><sitemap><loc>https://www.uu.nl/sitemap.xml?page=1</loc></sitemap></sitemapindex>"""
    child = """<urlset>
      <url><loc>https://www.uu.nl/en/masters/artificial-intelligence</loc></url>
      <url><loc>https://www.uu.nl/en/masters/computing-science</loc></url>
      <url><loc>https://www.uu.nl/en/masters/computing-science/application-and-admission</loc></url>
      <url><loc>https://www.uu.nl/en/masters/masters-programmes</loc></url>
    </urlset>"""
    rows = adapter.parse_catalog_from_fetcher(
        lambda url: index if url == adapter.catalog_url else child
    ).programmes
    assert [row.name for row in rows] == [
        "Artificial Intelligence",
        "Computing Science",
    ]


def test_msu_filters_tilda_catalogue_to_masters_across_slices() -> None:
    adapter = MSUAdapter(minimum_expected_programmes=2, page_size=1)
    page = '<script>var options={recid:"2066875221",storepart:"403521548872"};</script>'

    def product(uid: str, title: str, level: str) -> dict:
        return {
            "uid": uid,
            "title": title,
            "url": f"https://openday.msu.ru/programs/tproduct/{uid}",
            "characteristics": [
                {"title": "Faculty", "value": "Faculty of Science"},
                {"title": "Education level", "value": level},
            ],
        }

    payloads = [
        {"total": 3, "products": [product("1", "Data Science", "master's degree")]},
        {"total": 3, "products": [product("2", "Physics", "bachelor's degree")]},
        {"total": 3, "products": [product("3", "Biology", "master's degree")]},
    ]
    calls = iter(payloads)

    def fetcher(url: str) -> str:
        if url == adapter.catalog_url:
            return page
        return json.dumps(next(calls))

    rows = adapter.parse_catalog_from_fetcher(fetcher).programmes
    assert [row.name for row in rows] == ["Biology", "Data Science"]
