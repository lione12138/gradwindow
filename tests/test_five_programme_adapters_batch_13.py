from __future__ import annotations

from io import BytesIO

import pytest
from docx import Document

from gradwindow.programme_adapters.barcelona import BarcelonaAdapter
from gradwindow.programme_adapters.farabi import FarabiAdapter
from gradwindow.programme_adapters.montreal import MontrealAdapter
from gradwindow.programme_adapters.qub import QUBAdapter
from gradwindow.programme_adapters.wuhan import WuhanAdapter


def test_montreal_reads_master_routes_from_programme_sitemaps() -> None:
    adapter = MontrealAdapter(minimum_expected_programmes=2)
    root = """<sitemapindex>
      <loc>https://admission.umontreal.ca/sitemap.xml?sitemap=pages</loc>
      <loc>https://admission.umontreal.ca/sitemap.xml?sitemap=programmes</loc>
      <loc>https://admission.umontreal.ca/sitemap.xml?page=1&amp;sitemap=programmes</loc>
    </sitemapindex>"""
    first = """<urlset><loc>https://admission.umontreal.ca/programmes/
      maitrise-en-informatique/</loc></urlset>"""
    second = """<urlset><loc>https://admission.umontreal.ca/programmes/
      maitrise-en-histoire/</loc></urlset>"""

    def fetcher(url: str) -> str:
        if url == adapter.catalog_url:
            return root
        return second if "page=1" in url else first

    rows = adapter.parse_catalog_from_fetcher(fetcher).programmes
    assert [row.name for row in rows] == [
        "Maîtrise en histoire",
        "Maîtrise en informatique",
    ]
    assert rows[1].id == "umontreal-maitrise-informatique"


def test_barcelona_records_cloudflare_catalogue_limitation() -> None:
    rows = (
        BarcelonaAdapter()
        .parse_catalog("Content-Signal: search=yes,ai-train=no,use=reference\nAllow: /")
        .programmes
    )
    assert rows[0].name == "University master's degree catalogue"
    assert rows[0].parse_status == "no-deadline"


def test_wuhan_reads_both_official_docx_catalogues_and_exact_window() -> None:
    adapter = WuhanAdapter(
        minimum_expected_programmes=2,
        docx_fetcher=lambda url: _wuhan_docx("English" in url),
    )
    guide = """
      <h1>2026 Wuhan University Admissions Guide for International Applicants
      (Master’s and Doctoral Degrees)</h1>
      <p>Degree programs (Autumn 2026): Dec 1, 2025 – Jun 15, 2026</p>
      <a href="/English.docx">Graduate Programs Available to International
      Students at Wuhan University (English-taught).docx</a>
      <a href="/Chinese.docx">Master’s Programs Available to International
      Students at Wuhan University (Chinese-taught).docx</a>
    """
    rows = adapter.parse_catalog_from_fetcher(lambda url: guide).programmes
    assert [row.name for row in rows] == [
        "Computer Science (Chinese-taught)",
        "International Business (English-taught)",
        "International degree programmes",
    ]
    assert (rows[2].windows[0].opens_at, rows[2].windows[0].closes_at) == (
        "2025-12-01",
        "2026-06-15",
    )
    assert rows[2].id == "wuhan-computer-science-graduate"
    assert rows[0].windows == []
    assert rows[1].windows == []


def test_qub_rejects_an_aws_waf_challenge_as_catalogue_content() -> None:
    with pytest.raises(ValueError, match="access challenge"):
        QUBAdapter().parse_catalog(
            "window.awsWafCookieDomainList = ['www.qub.ac.uk','qub.ac.uk'];"
        )


def test_farabi_follows_all_master_catalogue_pages() -> None:
    adapter = FarabiAdapter(minimum_expected_programmes=2)
    first = """
      <a class="card" href="/en/education_programs/magistracy/speciality/1">
        <div class="code">7M03101</div><h2>Sociology</h2>
      </a><a href="?page=2">2</a>
    """
    second = """
      <a class="card" href="/en/education_programs/magistracy/speciality/2">
        <div class="code">7M06101</div><h2>Computer Science</h2>
      </a>
    """
    rows = adapter.parse_catalog_from_fetcher(
        lambda url: second if "page=2" in url else first
    ).programmes
    assert [row.name for row in rows] == [
        "Computer Science (7M06101)",
        "Sociology (7M03101)",
    ]


def _wuhan_docx(english: bool) -> bytes:
    document = Document()
    table = document.add_table(rows=2, cols=4 if not english else 3)
    if english:
        table.rows[0].cells[1].text = "Postgraduate Programs"
        table.rows[0].cells[2].text = "Duration"
        table.rows[1].cells[1].text = "International Business\n国际商务"
        table.rows[1].cells[2].text = "Two Years\n2年"
    else:
        table.rows[0].cells[1].text = "Programs"
        table.rows[0].cells[2].text = "Duration"
        table.rows[1].cells[1].text = "计算机科学\nComputer Science"
        table.rows[1].cells[2].text = "3年\nThree Years"
    payload = BytesIO()
    document.save(payload)
    return payload.getvalue()
