from __future__ import annotations

import pytest

from gradwindow.programme_adapters.base import OfficialSourceTransportError
from gradwindow.programme_adapters.cambridge import CambridgeAdapter, _reader_url

CAMBRIDGE_HTML = """
<html><body><table>
  <thead><tr><th>Course</th><th>Course Level</th><th>Taught/Research</th><th>Course Length</th></tr></thead>
  <tbody>
    <tr><td><a href="/courses/directory/egcempace">Advanced Chemical Engineering - Closed this cycle</a> MPhil</td><td>Master's</td><td>Taught</td><td>11 months full-time</td></tr>
    <tr><td><a href="/courses/directory/egegpdtwo">2D Materials of Tomorrow</a> PhD</td><td>Doctoral</td><td>Research</td><td>3 years</td></tr>
    <tr><td><a href="/courses/directory/icicdpgmf">(flexible) in Genomic Medicine - Closed this cycle</a> PGDip</td><td>Diploma</td><td></td><td>9 months</td></tr>
  </tbody>
</table></body></html>
"""

CAMBRIDGE_DETAIL = """
<html><body>
  <h1>MPhil in Advanced Computer Science</h1>
  <div>Applications open Sep. 3, 2025 Application deadline Feb. 26, 2026 Course starts Oct. 5, 2026</div>
</body></html>
"""

CAMBRIDGE_MULTI_INTAKE_DETAIL = """
<html><body>
  <h1>MPhil in Medical Science (Medicine)</h1>
  <div>Dates and deadlines:</div>
  <div>Lent 2026 (Closed)</div>
  <div>Applications open Sep. 4, 2024 Application deadline Oct. 2, 2025 Course starts Jan. 5, 2026</div>
  <div>Easter 2026 (Closed)</div>
  <div>Applications open Sep. 4, 2024 Application deadline Jan. 14, 2026 Course starts Apr. 17, 2026</div>
  <div>Michaelmas 2026 (Closed)</div>
  <div>Applications open Sep. 3, 2025 Application deadline May. 14, 2026 Course starts Oct. 1, 2026</div>
  <div>Lent 2027</div>
  <div>Applications open Sep. 3, 2025 Application deadline Oct. 1, 2026 Course starts Jan. 5, 2027</div>
  <div>Easter 2027</div>
  <div>Applications open Sep. 3, 2025 Application deadline Jan. 14, 2027 Course starts Apr. 17, 2027</div>
</body></html>
"""


def test_cambridge_adapter_extracts_taught_master_rows() -> None:
    catalog = CambridgeAdapter(minimum_expected_programmes=1).parse_catalog(
        CAMBRIDGE_HTML
    )

    assert len(catalog.programmes) == 1
    programme = catalog.programmes[0]
    assert programme.id == "cambridge-advanced-chemical-engineering-mphil"
    assert programme.name == "MPhil in Advanced Chemical Engineering"
    assert programme.windows == []
    assert programme.parse_status == "no-deadline"


def test_cambridge_adapter_can_fetch_paginated_directory() -> None:
    first_page = CAMBRIDGE_HTML.replace(
        "</body>",
        '<nav class="pager"><a href="?page=1">Last page</a></nav></body>',
    )
    second_page = CAMBRIDGE_HTML.replace(
        "Advanced Chemical Engineering",
        "Advanced Computer Science",
    ).replace("egcempace", "cscsmpacs")

    def fetcher(url: str) -> str:
        if "cscsmpacs" in url or "egcempace" in url:
            return CAMBRIDGE_DETAIL
        return second_page if "page=1" in url else first_page

    catalog = CambridgeAdapter(
        minimum_expected_programmes=2
    ).parse_catalog_from_fetcher(fetcher)

    assert {item.id for item in catalog.programmes} == {
        "cambridge-advanced-chemical-engineering-mphil",
        "cambridge-advanced-computer-science-mphil",
    }
    assert all(item.parse_status == "parsed" for item in catalog.programmes)
    assert catalog.programmes[0].windows[0].opens_at == "2025-09-03"
    assert catalog.programmes[0].windows[0].closes_at == "2026-02-26"
    assert catalog.programmes[0].windows[0].intake == "Michaelmas 2026"


def test_cambridge_adapter_extracts_all_target_academic_year_intakes() -> None:
    source_url = "https://www.postgraduate.study.cam.ac.uk/courses/directory/egcempace"

    def fetcher(url: str) -> str:
        if url == "https://www.postgraduate.study.cam.ac.uk/courses/directory":
            return CAMBRIDGE_HTML
        if url == source_url:
            return CAMBRIDGE_MULTI_INTAKE_DETAIL
        raise AssertionError(url)

    catalog = CambridgeAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
    ).parse_catalog_from_fetcher(fetcher)

    programme = catalog.programmes[0]
    assert [window.intake for window in programme.windows] == [
        "Michaelmas 2026",
        "Lent 2027",
        "Easter 2027",
    ]
    assert [window.closes_at for window in programme.windows] == [
        "2026-05-14",
        "2026-10-01",
        "2027-01-14",
    ]


def test_cambridge_adapter_uses_official_apply_subpage_after_course_page_403() -> None:
    source_url = "https://www.postgraduate.study.cam.ac.uk/courses/directory/egcempace"
    apply_url = f"{source_url}/apply"

    def fetcher(url: str) -> str:
        if url == "https://www.postgraduate.study.cam.ac.uk/courses/directory":
            return CAMBRIDGE_HTML
        if url == source_url:
            raise RuntimeError("HTTP 403")
        if url == apply_url:
            return CAMBRIDGE_DETAIL
        raise AssertionError(url)

    catalog = CambridgeAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
    ).parse_catalog_from_fetcher(fetcher)

    programme = catalog.programmes[0]
    assert programme.parse_status == "parsed"
    assert programme.retrieval_method == "official-course-apply-page"
    assert programme.windows[0].source_url == apply_url


def test_cambridge_adapter_uses_reader_only_after_official_transport_failures() -> None:
    source_url = "https://www.postgraduate.study.cam.ac.uk/courses/directory/egcempace"
    apply_url = f"{source_url}/apply"

    def fetcher(url: str) -> str:
        if url == "https://www.postgraduate.study.cam.ac.uk/courses/directory":
            return CAMBRIDGE_HTML
        if url in {source_url, apply_url}:
            raise RuntimeError("HTTP 403")
        if url == _reader_url(apply_url):
            return CAMBRIDGE_DETAIL
        raise AssertionError(url)

    catalog = CambridgeAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
    ).parse_catalog_from_fetcher(fetcher)

    programme = catalog.programmes[0]
    assert programme.parse_status == "parsed"
    assert programme.retrieval_method == "official-course-apply-page-via-reader"
    assert programme.windows[0].source_url == apply_url


def test_cambridge_adapter_uses_browser_rendering_before_reader_fallback() -> None:
    source_url = "https://www.postgraduate.study.cam.ac.uk/courses/directory/egcempace"
    apply_url = f"{source_url}/apply"

    def fetcher(url: str) -> str:
        if url == "https://www.postgraduate.study.cam.ac.uk/courses/directory":
            return CAMBRIDGE_HTML
        if url in {source_url, apply_url}:
            raise RuntimeError("HTTP 403")
        raise AssertionError("reader fallback should not run")

    catalog = CambridgeAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
        browser_markdown_fetcher=lambda url: (
            CAMBRIDGE_DETAIL if url == apply_url else ""
        ),
    ).parse_catalog_from_fetcher(fetcher)

    programme = catalog.programmes[0]
    assert programme.parse_status == "parsed"
    assert programme.retrieval_method == "cloudflare-browser-rendering"
    assert programme.windows[0].source_url == apply_url


def test_cambridge_adapter_renders_apply_page_when_course_page_has_no_dates() -> None:
    source_url = "https://www.postgraduate.study.cam.ac.uk/courses/directory/egcempace"
    apply_url = f"{source_url}/apply"

    def fetcher(url: str) -> str:
        if url == "https://www.postgraduate.study.cam.ac.uk/courses/directory":
            return CAMBRIDGE_HTML
        if url == source_url:
            return "<main>Course overview without application dates.</main>"
        if url == apply_url:
            raise RuntimeError("HTTP 403")
        raise AssertionError("reader fallback should not run")

    catalog = CambridgeAdapter(
        minimum_expected_programmes=1,
        detail_workers=1,
        browser_markdown_fetcher=lambda url: (
            CAMBRIDGE_DETAIL if url == apply_url else ""
        ),
    ).parse_catalog_from_fetcher(fetcher)

    programme = catalog.programmes[0]
    assert programme.parse_status == "parsed"
    assert programme.retrieval_method == "cloudflare-browser-rendering"


def test_cambridge_adapter_classifies_complete_source_access_failure() -> None:
    def fetcher(url: str) -> str:
        if url == "https://www.postgraduate.study.cam.ac.uk/courses/directory":
            return CAMBRIDGE_HTML
        raise RuntimeError("HTTP 403")

    with pytest.raises(OfficialSourceTransportError, match="Cambridge official"):
        CambridgeAdapter(
            minimum_expected_programmes=1,
            detail_workers=1,
        ).parse_catalog_from_fetcher(fetcher)
