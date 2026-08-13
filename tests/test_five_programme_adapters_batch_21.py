from __future__ import annotations

import json

from gradwindow.programme_adapters.grenoble_alpes import GrenobleAlpesAdapter
from gradwindow.programme_adapters.hunan import HunanAdapter
from gradwindow.programme_adapters.mainz import MainzAdapter
from gradwindow.programme_adapters.uestc import EXPECTED_GUIDE_SHA256, UESTCAdapter
from gradwindow.programme_adapters.umass_amherst import (
    ADMISSIONS_POLICY_URL,
    UMassAmherstAdapter,
)


def test_uestc_uses_only_visually_verified_masters_and_exact_shared_window() -> None:
    adapter = UESTCAdapter(
        minimum_expected_programmes=15,
        maximum_expected_programmes=15,
        guide_hash_fetcher=lambda _url: EXPECTED_GUIDE_SHA256,
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: "").programmes

    catalogue_rows = [row for row in rows if not row.windows]
    assert len(catalogue_rows) == 15
    assert "Electronic Science and Technology" in {row.name for row in catalogue_rows}
    group = next(row for row in rows if row.windows)
    assert (group.windows[0].opens_at, group.windows[0].closes_at) == (
        "2025-12-01",
        "2026-03-01",
    )
    assert group.evidence_document_hash == EXPECTED_GUIDE_SHA256


def test_hunan_deduplicates_catalogue_rows_and_keeps_two_official_rounds() -> None:
    entries = (
        ("岳麓书院", "010100", "哲学", "全日制"),
        ("法学院", "035101", "法律（非法学）", "全日制"),
        ("法学院", "035101", "法律（非法学）", "非全日制"),
    )
    guide = """
      <h1>湖南大学2026年硕士研究生招生简章</h1>
      <p>预报名时间：2025年10月10日至10月13日</p>
      <p>正式报名时间：2025年10月16日至10月27日</p>
    """
    adapter = HunanAdapter(
        minimum_expected_programmes=3,
        maximum_expected_programmes=3,
        catalogue_fetcher=lambda _url: entries,
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: guide).programmes

    catalogue_rows = [row for row in rows if not row.windows]
    assert {row.name for row in catalogue_rows} == {
        "哲学（全日制）",
        "法律（非法学）（全日制）",
        "法律（非法学）（非全日制）",
    }
    group = next(row for row in rows if row.windows)
    assert [(window.opens_at, window.closes_at) for window in group.windows] == [
        ("2025-10-10", "2025-10-13"),
        ("2025-10-16", "2025-10-27"),
    ]


def test_mainz_reads_master_api_records_and_exact_summer_routes() -> None:
    payload = [
        {
            "id": "m1",
            "fieldOfStudy": "Data Science",
            "degree": "Master of Science",
            "zulassungsv_link": "https://www.studium.uni-mainz.de/data-science/",
            "faechergruppen": "Science",
            "zulassungsmodus": "O",
            "zulassungssemester": "Sommer- und Wintersemester",
        },
        {
            "id": "m2",
            "fieldOfStudy": "Law",
            "degree": "Master of Laws",
            "zulassungsv_link": "https://www.studium.uni-mainz.de/law/",
            "faechergruppen": "Law",
            "zulassungsmodus": "X",
            "zulassungssemester": "nur Sommersemester",
        },
        {
            "id": "b1",
            "fieldOfStudy": "History",
            "degree": "Bachelor of Arts",
            "zulassungsv_link": "https://www.studium.uni-mainz.de/history/",
            "faechergruppen": "Humanities",
            "zulassungsmodus": "O",
            "zulassungssemester": "Wintersemester",
        },
    ]
    dates = """
      <p>the application periods for master's degree programs change on a
      one-time basis for the summer semester 2027:</p>
      <p>Master's degree programs with restricted admission (including those
      with an aptitude test / interview): November 09, 2026 to December 04, 2026</p>
      <p>Master's degree programs without admission restrictions:
      November 09, 2026 to March 01, 2027</p>
    """

    def fetcher(url: str) -> str:
        return json.dumps(payload) if "wp-json" in url else dates

    rows = (
        MainzAdapter(minimum_expected_programmes=2, maximum_expected_programmes=2)
        .parse_catalog_from_fetcher(fetcher)
        .programmes
    )

    assert {row.name for row in rows if not row.windows} == {"Data Science", "Law"}
    groups = [row for row in rows if row.windows]
    assert [(row.windows[0].opens_at, row.windows[0].closes_at) for row in groups] == [
        ("2026-11-09", "2026-12-04"),
        ("2026-11-09", "2027-03-01"),
    ]


def test_umass_reads_only_official_bulletin_master_fields() -> None:
    html = """
      <div class="printcontent">
        <h2>Major Fields Leading to the Degree of Doctor of Philosophy</h2>
        <p><a href="?topicgroupid=1">Astronomy</a></p>
        <h2>Major Fields in which Courses Are Offered Leading to the Master’s Degree</h2>
        <p>
          <a href="?topicgroupid=2">Accounting</a>
          <a href="?topicgroupid=3">Art Education</a>
        </p>
      </div>
    """

    rows = (
        UMassAmherstAdapter(minimum_expected_programmes=2)
        .parse_catalog(html)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Accounting", "Master"),
        ("Art Education", "Master"),
    ]


def test_umass_requires_official_programme_specific_deadline_guidance() -> None:
    html = """
      <div class="printcontent">
        <h2>Major Fields in which Courses Are Offered Leading to the Master’s Degree</h2>
        <p><a href="?topicgroupid=2">Accounting</a></p>
      </div>
    """
    guidance = """
      <p>The deadline for the summer/fall entrance cycle, varies by program.</p>
      <p>Refer to the Academics page for specific deadlines.</p>
    """
    adapter = UMassAmherstAdapter(
        minimum_expected_programmes=1, maximum_expected_programmes=4
    )

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: guidance if url == ADMISSIONS_POLICY_URL else html
    ).programmes

    assert [(row.name, row.degree_type) for row in rows] == [("Accounting", "Master")]


def test_grenoble_reads_master_mentions_and_checks_application_routing() -> None:
    html = """
      <a href="/fr/catalogue/master/data-X.html">Master Data science</a>
      <a href="/fr/catalogue/licence/history-X.html">Licence Histoire</a>
    """
    guidance = "Apply for the first year of a Master's degree via Mon Master."
    adapter = GrenobleAlpesAdapter(minimum_expected_programmes=1)

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: guidance if url == adapter.application_url else html
    ).programmes

    assert [(row.name, row.degree_type) for row in rows] == [("Data science", "Master")]
