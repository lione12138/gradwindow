from __future__ import annotations

from gradwindow.programme_adapters.cau import CAUAdapter
from gradwindow.programme_adapters.central_south import CentralSouthAdapter
from gradwindow.programme_adapters.dlut import DLUTAdapter
from gradwindow.programme_adapters.eduhk import EdUHKAdapter
from gradwindow.programme_adapters.seu import EXPECTED_GUIDE_SHA256, SEUAdapter


def test_central_south_deduplicates_research_fields_at_major_scope() -> None:
    entries = (
        ("School of Public Administration", "Sociology", "Social Policy", "Chinese"),
        (
            "School of Public Administration",
            "Sociology",
            "Social Governance",
            "Chinese",
        ),
        ("School of Public Administration", "Sociology", "Social Policy", "English"),
    )
    guide = """
      <h1>2026 Application Guide to International Graduate Programs</h1>
      <p>High-Level Graduates Program: From now on to February 15, 2026</p>
      <p>CSU Scholarship and Self-sponsored: From now on to May 31, 2026</p>
    """
    adapter = CentralSouthAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda _url: entries,
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: guide).programmes

    catalogue_rows = [row for row in rows if not row.windows]
    assert [row.name for row in catalogue_rows] == [
        "Sociology (Chinese-medium)",
        "Sociology (English-medium)",
    ]
    review_rows = [row for row in rows if row.windows]
    assert [row.windows[0].closes_at for row in review_rows] == [
        "2026-02-15",
        "2026-05-31",
    ]
    assert all(row.windows[0].opens_at is None for row in review_rows)


def test_cau_reads_only_rows_with_a_master_duration() -> None:
    html = """
      <h1>2026 China Agricultural University Admission Information for Graduate</h1>
      <p>China Government Scholarship: Nov 2025 to Feb 2026.</p>
      <table></table><table></table><table></table><table></table>
      <table>
        <tr><th>Colleges</th><th>Major</th><th>Master</th><th>Ph.D</th></tr>
        <tr><td>Agronomy and Biotechnology</td><td>Crop Science</td><td>3 Years</td><td>4 Years</td></tr>
        <tr><td></td><td>Plant Nutrition</td><td>/</td><td>4 Years</td></tr>
      </table>
      <table>
        <tr><th>Chinese-Taught Programs</th></tr>
        <tr><th>Colleges</th><th>Major</th><th>Master</th><th>Ph.D</th></tr>
        <tr><td>Engineering</td><td>Mechanical Engineering</td><td>3 years</td><td>4 years</td></tr>
      </table>
    """

    rows = (
        CAUAdapter(
            minimum_expected_programmes=2,
            maximum_expected_programmes=2,
        )
        .parse_catalog(html)
        .programmes
    )

    assert [row.name for row in rows] == [
        "Crop Science (English-medium)",
        "Mechanical Engineering (Chinese-medium)",
    ]
    assert all(not row.windows for row in rows)


def test_seu_keeps_catalogue_rows_and_verified_exact_group_window() -> None:
    entries = (
        ("School of Transportation", "Transportation Engineering", "3"),
        ("School of Public Health", "Public Health (English-taught)", "2"),
    )
    adapter = SEUAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda _url: entries,
        guide_hash_fetcher=lambda _url: EXPECTED_GUIDE_SHA256,
    )
    catalog_page = '<span pdfsrc="/official-masters.pdf"></span>'
    guide_page = '<span pdfsrc="/official-2026-guide.pdf"></span>'

    def fetcher(url: str) -> str:
        return guide_page if "546671" in url else catalog_page

    rows = adapter.parse_catalog_from_fetcher(fetcher).programmes

    group = next(row for row in rows if row.windows)
    assert (group.windows[0].opens_at, group.windows[0].closes_at) == (
        "2025-11-22",
        "2026-05-15",
    )
    assert group.windows[0].opens_at_basis == "official"


def test_dlut_keeps_teaching_language_variants_and_csc_window() -> None:
    entries = (
        ("School of Mechanics", "Mechanics", "Chinese"),
        ("School of Mechanics", "Mechanics", "English"),
    )
    guide = """
      <h1>Chinese University Program 2026</h1>
      <p>Application Time From November 1, 2025 to February 15, 2026.</p>
    """
    adapter = DLUTAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda _urls: entries,
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: guide).programmes

    assert [row.name for row in rows if not row.windows] == [
        "Mechanics (Chinese-medium)",
        "Mechanics (English-medium)",
    ]
    group = next(row for row in rows if row.windows)
    assert group.windows[0].applicant_categories == ["chinese-government-scholarship"]
    assert group.windows[0].opens_at == "2025-11-01"


def test_eduhk_reads_taught_masters_and_keeps_missing_open_date() -> None:
    html = """
      <div id="content_box_19">
        <h2>Taught Postgraduate Programmes</h2>
        <a class="faq_in_text" href="/programme/a"><span class="title">Master of Arts in Education [MAE] #</span></a>
        <a class="faq_in_text" href="/programme/b"><span class="title">Master of Science in Education [MScE]</span></a>
        <a class="faq_in_text" href="/doctorate"><span class="title">Doctor of Education [EdD]</span></a>
      </div>
    """
    schedule_text = """
      Admission Schedule for Taught Postgraduate Programmes 2026/27
      October 2025 Open for applications
      10 May 2026 Application Deadline for Non-local Applicants
      31 May 2026 Application Deadline for Local Applicants
    """
    adapter = EdUHKAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda _url: html,
        schedule_fetcher=lambda _url: schedule_text,
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: "").programmes

    assert [row.name for row in rows if not row.windows] == [
        "Master of Arts in Education [MAE]",
        "Master of Science in Education [MScE]",
    ]
    review_rows = [row for row in rows if row.windows]
    assert [row.windows[0].closes_at for row in review_rows] == [
        "2026-05-10",
        "2026-05-31",
    ]
    assert all(row.windows[0].opens_at_basis == "missing" for row in review_rows)
