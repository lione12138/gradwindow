from __future__ import annotations

from gradwindow.programme_adapters.cologne import CologneAdapter
from gradwindow.programme_adapters.gothenburg import GothenburgAdapter
from gradwindow.programme_adapters.munster import MunsterAdapter
from gradwindow.programme_adapters.strasbourg import StrasbourgAdapter
from gradwindow.programme_adapters.utah import (
    APPLICATION_URL as UTAH_APPLICATION_URL,
)
from gradwindow.programme_adapters.utah import (
    DIRECTORY_DATA_URL,
    KAHLERT_DEADLINE_URL,
    UtahAdapter,
)


def test_cologne_splits_master_degree_from_official_card_label() -> None:
    html = """
      <article class="c-card"><a class="c-card__link" href="?id=1">
        Data Science, Master of Science (M.Sc.)</a></article>
      <article class="c-card"><a class="c-card__link" href="?id=2">
        History, Bachelor of Arts (B.A.)</a></article>
    """

    rows = CologneAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Data Science", "Master of Science (M.Sc.)")
    ]


def test_munster_keeps_distinct_master_variants() -> None:
    html = """
      <table><tr><td>Education</td><td></td><td>
        <a href="?nr=1" title="Master of Education (Primary)">MEd(G)</a>
        <a href="?nr=2" title="Master of Education (Secondary)">MEd(GymGe)</a>
      </td></tr></table>
    """

    rows = MunsterAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Education (MEd(G))", "Master of Education (Primary)"),
        ("Education (MEd(GymGe))", "Master of Education (Secondary)"),
    ]


def test_gothenburg_deduplicates_category_links_by_official_url() -> None:
    html = """
      <main id="main">
        <a href="/en/study-gothenburg/data-science-masters-programme">
          Data Science (External link)</a>
        <a href="/en/study-gothenburg/data-science-masters-programme">
          Data Science</a>
      </main>
    """

    rows = (
        GothenburgAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [("Data Science", "Master")]


def test_strasbourg_reads_top_level_master_mentions_only() -> None:
    html = """
      <article><h2><a href="/fr/master/data/">Master Science des données</a></h2>
        <ul class="subprograms"><li>Track A</li><li>Track B</li></ul></article>
    """

    rows = (
        StrasbourgAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Science des données", "Master")
    ]


def test_utah_keeps_only_master_degree_cards() -> None:
    html = """
      <div class="c-grid-layout__cell bg-white"><h3>
        <span aria-hidden="true"><span>icon</span></span>
        <span class="sr-only">Available online</span>
        <a href="/ms/">Computing MS</a></h3>
        <p class="h6">Master of Science</p></div>
      <div class="c-grid-layout__cell bg-white"><h3><a href="/phd/">Computing PhD</a></h3>
        <p class="h6">Doctor of Philosophy</p></div>
      <div class="c-grid-layout__cell bg-white"><h3>Biotechnology PSM</h3>
        <p class="h6">Professional Science Master's</p></div>
    """

    rows = UtahAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.degree_type, row.source_url) for row in rows] == [
        ("Biotechnology PSM", "Professional Science Master's", UtahAdapter.catalog_url),
        ("Computing MS", "Master of Science", "https://gradschool.utah.edu/ms/"),
    ]


def test_utah_fetches_the_official_directory_data_endpoint() -> None:
    pages = {
        DIRECTORY_DATA_URL: """
          <div class="c-grid-layout__cell bg-white">
            <h3><a href="/ms/">Computing MS</a></h3>
            <p class="h6">Master of Science</p>
          </div>
          <div class="c-grid-layout__cell">
            <h3>Computer Science MS</h3>
            <p class="h6">Master of Science</p>
          </div>
        """,
        UTAH_APPLICATION_URL: (
            "Each graduate program sets its own application deadlines. "
            "Use the online application system."
        ),
        KAHLERT_DEADLINE_URL: (
            "Applications for Fall 2027 will have to be submitted between "
            "September and December 15, 2026."
        ),
    }
    fetched = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        return pages[url]

    rows = UtahAdapter(minimum_expected_programmes=1).parse_catalog_from_fetcher(
        fetcher
    )

    computing = {item.name: item for item in rows.programmes}

    assert len(rows.programmes) == 2
    assert computing["Computer Science MS"].parse_status == "incomplete"
    assert computing["Computer Science MS"].windows[0].closes_at == "2026-12-15"
    assert computing["Computer Science MS"].windows[0].opens_at is None
    assert computing["Computing MS"].parse_status == "incomplete"
    assert fetched == [
        DIRECTORY_DATA_URL,
        UTAH_APPLICATION_URL,
        KAHLERT_DEADLINE_URL,
    ]
