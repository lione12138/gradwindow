from __future__ import annotations

import json

from gradwindow.programme_adapters.beihang import BeihangAdapter
from gradwindow.programme_adapters.bit import BITAdapter
from gradwindow.programme_adapters.bit import GuidePayload as BITGuidePayload
from gradwindow.programme_adapters.bnu import CATALOG_URL as BNU_CATALOG_URL
from gradwindow.programme_adapters.bnu import GUIDE_URL as BNU_GUIDE_URL
from gradwindow.programme_adapters.bnu import BNUAdapter
from gradwindow.programme_adapters.jilin import CATALOG_URL as JILIN_CATALOG_URL
from gradwindow.programme_adapters.jilin import GUIDE_URL as JILIN_GUIDE_URL
from gradwindow.programme_adapters.jilin import GuidePayload as JilinGuidePayload
from gradwindow.programme_adapters.jilin import JilinAdapter
from gradwindow.programme_adapters.xiamen import (
    CHINESE_CATALOG_URL,
    ENGLISH_CATALOG_URL,
    XiamenAdapter,
)
from gradwindow.programme_adapters.xiamen import (
    GUIDE_URL as XIAMEN_GUIDE_URL,
)


def test_bnu_deduplicates_research_directions_and_adds_group_window() -> None:
    workbook = json.dumps(
        {
            "worksheets": [
                {
                    "name": "Sheet1",
                    "rows": [
                        [None, "001 School of Philosophy", None],
                        [None, "010100 Philosophy", None],
                        [None, "01 Philosophy of Marxism", "Chinese"],
                        [None, "010100 Philosophy", None],
                        [None, "02 Chinese Philosophy", "Chinese"],
                        [None, "002 Faculty of Education", None],
                        [None, "040100 Education", None],
                    ],
                }
            ]
        }
    )
    guide = (
        "<p>Online Application Period From November 15, 202 5 to March 10, 202 6</p>"
    )
    pages = {BNU_CATALOG_URL: workbook, BNU_GUIDE_URL: guide}

    catalog = BNUAdapter(
        minimum_expected_programmes=2, maximum_expected_programmes=3
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert [programme.name for programme in catalog.programmes[:-1]] == [
        "Education",
        "Philosophy",
    ]
    window = catalog.programmes[-1].windows[0]
    assert (window.opens_at, window.closes_at) == ("2025-11-15", "2026-03-10")


def test_beihang_reads_bilingual_marker_layout_without_research_directions() -> None:
    pdf_text = """
      School of Materials Science and Engineering
      http://www.mse.buaa.edu.cn/
      Materials Science and
      Engineering \u25cf\u25b2
      \u6750\u6599\u79d1\u5b66\u4e0e\u5de5\u7a0b
      (1) High-temperature structural materials and coating technology
      Legal Theory \u25cf
      \u6cd5\u5b66\u7406\u8bba
      \u7535\u5b50\u4fe1\u606f\u25cf\u25b2
      Electronic Information
    """
    guide = """
      <p>Online Application Start Date: November 1, 2025</p>
      <p>Application Deadline: June 30, 2026</p>
    """
    catalog = BeihangAdapter(
        minimum_expected_programmes=3,
        maximum_expected_programmes=3,
        pdf_text_fetcher=lambda _url: pdf_text,
    ).parse_catalog_from_fetcher(lambda _url: guide)

    assert {programme.name for programme in catalog.programmes[:-1]} == {
        "Materials Science and Engineering",
        "Legal Theory",
        "Electronic Information",
    }
    assert catalog.programmes[-1].windows[0].opens_at == "2025-11-01"


def test_bit_keeps_campus_offerings_and_shared_exact_window() -> None:
    payload = BITGuidePayload(
        entries=(
            ("Beijing Campus", "Mechanical Engineering"),
            ("Zhuhai Campus", "Mechanical Engineering"),
            ("Beijing Campus", "Law"),
        )
    )
    guide = "<p>Application Period: October 15th, 2025 to June 1st, 2026</p>"
    catalog = BITAdapter(
        minimum_expected_programmes=3,
        maximum_expected_programmes=3,
        guide_fetcher=lambda _url: payload,
    ).parse_catalog_from_fetcher(lambda _url: guide)

    assert len({programme.id for programme in catalog.programmes[:-1]}) == 3
    window = catalog.programmes[-1].windows[0]
    assert (window.opens_at, window.closes_at) == ("2025-10-15", "2026-06-01")


def test_jilin_keeps_close_only_guidance_when_opening_is_unpublished() -> None:
    payload = JilinGuidePayload(
        entries=(
            ("School of Law", "International Law"),
            ("College of Engineering", "Mechanical Engineering"),
        )
    )
    catalogue = """
      <a href="/system/download.jsp?file=2026.pdf">
        2026-2027 Jilin University International Catalogue PDF
      </a>
    """
    guide = "<p>Application Time Deadline: Ju ne 30, 202 6</p>"
    pages = {JILIN_CATALOG_URL: catalogue, JILIN_GUIDE_URL: guide}
    catalog = JilinAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        guide_fetcher=lambda _url: payload,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    window = catalog.programmes[-1].windows[0]
    assert window.opens_at is None
    assert window.closes_at == "2026-06-30"
    assert window.opens_at_basis == "missing"
    assert catalog.programmes[-1].parse_status == "incomplete"


def test_xiamen_parses_rowspan_catalogues_and_three_exact_rounds() -> None:
    chinese = """
      <table>
        <tr><th>No.</th><th>Location</th><th>School</th><th>Department</th>
          <th>Code</th><th>Program</th><th>Duration</th><th>Mode</th><th>Contact</th></tr>
        <tr><td>1</td><td>Siming Campus</td><td>School of Law</td>
          <td>School of Law</td><td>030100</td><td>Law</td><td>3</td>
          <td>Full-time</td><td>Admissions</td></tr>
        <tr><td>2</td><td>035102</td><td>Juris Master</td></tr>
      </table>
    """
    english = """
      <table><tr><th>No.</th><th>Location</th><th>School</th><th>Department</th>
        <th>Code</th><th>Program</th><th>Duration</th><th>Mode</th><th>Contact</th></tr>
        <tr><td>1</td><td>Siming Campus</td><td>School of Law</td>
          <td>School of Law</td><td>0301Z2</td><td>Fiscal and Tax Law</td>
          <td>2</td><td>Full-time</td><td>Admissions</td></tr></table>
    """
    guide_html = """
      <script>showVsbpdfIframe('/virtual_attach_file.vsb?e=.pdf', []);</script>
    """
    guide_text = """
      II. Application Timeline Start Time Deadline Scholarship Category
      Dec. 1, 2025 Feb. 15, 2026 Chinese Government Scholarships
      Apr. 10, 2026 University Scholarships
      May 10, 2026 Self-funded
    """
    pages = {
        CHINESE_CATALOG_URL: chinese,
        ENGLISH_CATALOG_URL: english,
        XIAMEN_GUIDE_URL: guide_html,
        "https://admissions.xmu.edu.cn/virtual_attach_file.vsb?e=.pdf": guide_text,
    }
    catalog = XiamenAdapter(
        minimum_expected_programmes=3, maximum_expected_programmes=3
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 4
    assert [window.closes_at for window in catalog.programmes[-1].windows] == [
        "2026-02-15",
        "2026-04-10",
        "2026-05-10",
    ]
    assert all(
        window.opens_at == "2025-12-01" for window in catalog.programmes[-1].windows
    )
