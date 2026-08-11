from __future__ import annotations

from gradwindow.programme_adapters.cologne import CologneAdapter
from gradwindow.programme_adapters.gothenburg import GothenburgAdapter
from gradwindow.programme_adapters.munster import MunsterAdapter
from gradwindow.programme_adapters.strasbourg import StrasbourgAdapter
from gradwindow.programme_adapters.utah import UtahAdapter


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
      <div class="c-grid-layout__cell bg-white"><h3><a href="/ms/">Computing MS</a></h3>
        <p class="h6">Master of Science</p></div>
      <div class="c-grid-layout__cell bg-white"><h3><a href="/phd/">Computing PhD</a></h3>
        <p class="h6">Doctor of Philosophy</p></div>
    """

    rows = UtahAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Computing MS", "Master of Science")
    ]
