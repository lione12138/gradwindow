from __future__ import annotations

from gradwindow.programme_adapters.lshtm import LSHTMAdapter
from gradwindow.programme_adapters.milan import MilanAdapter
from gradwindow.programme_adapters.pumc import PUMCAdapter
from gradwindow.programme_adapters.qut import QUTAdapter
from gradwindow.programme_adapters.zhengzhou import ZhengzhouAdapter


def test_milan_reads_only_masters_from_the_official_application_portal() -> None:
    html = """
      <div class="item">
        <a href="/courses/course/1-data-science">
          <span class="awards label">DS</span> Data Science
        </a>
        <small><div class="item">Master's (Laurea magistrale), full-time</div>
        <div class="item">Faculty of Science and Technology</div></small>
      </div>
      <div class="item">
        <a href="/courses/course/1-data-science">Data Science</a>
        <small><div class="item">Master's (Laurea magistrale), full-time</div>
        <div class="item">Faculty of Science and Technology</div></small>
      </div>
      <div class="item">
        <a href="/courses/course/2-economics">Economics</a>
        <small><div class="item">Bachelor's, full-time</div></small>
      </div>
    """

    rows = MilanAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.faculty) for row in rows] == [
        ("Data Science", "Faculty of Science and Technology")
    ]
    assert rows[0].source_url.endswith("/courses/course/1-data-science")


def test_lshtm_validates_the_prospectus_before_emitting_taught_masters() -> None:
    titles = (
        "MSc Epidemiology",
        "MSc Public Health",
        "MSc Veterinary Epidemiology",
    )
    adapter = LSHTMAdapter(
        expected_programmes=titles,
        prospectus_text_fetcher=lambda _url: " | ".join(titles),
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: "unused").programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Epidemiology", "MSc"),
        ("Public Health", "MSc"),
        ("Veterinary Epidemiology", "MSc"),
    ]
    assert all(row.source_url == adapter.catalog_url for row in rows)


def test_qut_reads_the_official_online_masters_subset() -> None:
    html = """
      <a href="/online-courses/it/master-of-information-technology/">
        Master of Information Technology
      </a>
      <a href="/online-courses/it/master-of-information-technology/">
        Master of Information Technology
      </a>
      <a href="/online-courses/it/graduate-certificate/">
        Graduate Certificate in Information Technology
      </a>
    """

    rows = QUTAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [row.name for row in rows] == ["Master of Information Technology"]
    assert rows[0].source_url.startswith("https://online.qut.edu.au/")


def test_zhengzhou_monitors_captcha_catalogues_and_national_dates() -> None:
    directory = """
      <h1>郑州大学2026年硕士研究生招生专业目录</h1>
      <a href="/system/_content/download.jsp?wbfileid=1">001商学院专业目录.pdf</a>
      <a href="/system/_content/download.jsp?wbfileid=2">002法学院专业目录.pdf</a>
    """
    guide = """
      网上预报名时间：2025年10月10日至10月13日。
      网上报名时间：2025年10月16日至10月27日。
    """
    adapter = ZhengzhouAdapter(minimum_expected_catalogues=2)

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: guide if url == adapter.guide_url else directory
    ).programmes

    assert rows[0].id == "zhengzhou-2026-master-catalogue"
    assert not rows[0].windows
    group = next(row for row in rows if row.windows)
    assert [(window.opens_at, window.closes_at) for window in group.windows] == [
        ("2025-10-10", "2025-10-13"),
        ("2025-10-16", "2025-10-27"),
    ]


def test_pumc_monitors_captcha_catalogue_and_national_dates() -> None:
    directory = """
      <h1>北京协和医学院2026年统招硕士研究生招生专业目录</h1>
      <a href="/system/_content/download.jsp?wbfileid=4597190">
        北京协和医学院2026年统招硕士研究生招生专业目录.pdf
      </a>
    """
    guide = """
      网上预报名时间：2025年10月10日至10月13日。
      网上报名时间：2025年10月16日至10月27日。
    """
    adapter = PUMCAdapter()

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: guide if url == adapter.guide_url else directory
    ).programmes

    assert rows[0].id == "pumc-2026-master-catalogue"
    assert rows[0].evidence_quality == "official-access-limitation"
    group = next(row for row in rows if row.windows)
    assert [(window.opens_at, window.closes_at) for window in group.windows] == [
        ("2025-10-10", "2025-10-13"),
        ("2025-10-16", "2025-10-27"),
    ]
