from __future__ import annotations

from gradwindow.programme_adapters.calgary import (
    APPLICATION_URL as CALGARY_APPLICATION_URL,
)
from gradwindow.programme_adapters.calgary import CATALOG_URL as CALGARY_CATALOG_URL
from gradwindow.programme_adapters.calgary import CalgaryAdapter
from gradwindow.programme_adapters.leicester import (
    APPLICATION_URL as LEICESTER_APPLICATION_URL,
)
from gradwindow.programme_adapters.leicester import (
    CATALOG_URL as LEICESTER_CATALOG_URL,
)
from gradwindow.programme_adapters.leicester import LeicesterAdapter
from gradwindow.programme_adapters.tufts import APPLICATION_URL as TUFTS_APPLICATION_URL
from gradwindow.programme_adapters.tufts import CATALOG_URL as TUFTS_CATALOG_URL
from gradwindow.programme_adapters.tufts import TuftsAdapter
from gradwindow.programme_adapters.twente import (
    APPLICATION_URL as TWENTE_APPLICATION_URL,
)
from gradwindow.programme_adapters.twente import CATALOG_URL as TWENTE_CATALOG_URL
from gradwindow.programme_adapters.twente import TwenteAdapter
from gradwindow.programme_adapters.ucsc import UCSCAdapter


def test_twente_reads_top_level_msc_cards_only() -> None:
    pages = {
        TWENTE_CATALOG_URL: (
            _twente_card("Applied Mathematics", "MSc", "/applied-mathematics/")
            + _twente_card(
                "Data Science",
                "MSc",
                "/programmes/applied-mathematics/specialisation/data-science/",
            )
            + _twente_card("Joint Programme", "MSc", "https://joint.example/programme")
            + _twente_card("Responsible Futures", "Certificate", "/insert/")
        ),
        TWENTE_APPLICATION_URL: _twente_deadlines(),
    }

    rows = (
        TwenteAdapter(minimum_expected_programmes=1, target_cycle_year=2027)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type, row.source_url) for row in rows] == [
        (
            "Applied Mathematics",
            "MSc",
            "https://www.utwente.nl/applied-mathematics/",
        ),
        ("Joint Programme", "MSc", TWENTE_CATALOG_URL),
    ]
    assert [
        (
            window.intake,
            window.applicant_categories,
            window.opens_at,
            window.closes_at,
            window.opens_at_basis,
            window.deadline_semantics,
        )
        for window in rows[0].windows
    ] == [
        (
            "February 2027",
            ["eu-efta"],
            "2026-03-01",
            "2026-12-01",
            "official-recurring-policy",
            "before",
        ),
        (
            "February 2027",
            ["non-eu-efta"],
            "2026-03-01",
            "2026-10-01",
            "official-recurring-policy",
            "before",
        ),
        (
            "September 2027",
            ["eu-efta"],
            "2026-10-01",
            "2027-07-01",
            "official-recurring-policy",
            "before",
        ),
        (
            "September 2027",
            ["non-eu-efta"],
            "2026-10-01",
            "2027-05-01",
            "official-recurring-policy",
            "before",
        ),
    ]


def test_leicester_follows_pagination_and_filters_master_credentials() -> None:
    second_url = "https://le.ac.uk/courses?Page=2&level=Postgraduate"
    pages = {
        LEICESTER_CATALOG_URL: _leicester_card("Data Science MSc", "/data")
        + f'<a class="pagination__link--next" href="{second_url}">Next</a>',
        second_url: _leicester_card("Clinical Psychology DClinPsy", "/clinical"),
        LEICESTER_APPLICATION_URL: "Choose a course and apply online.",
    }

    rows = (
        LeicesterAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [("Data Science", "MSc")]


def test_calgary_follows_pager_and_keeps_master_cards() -> None:
    second_url = f"{CALGARY_CATALOG_URL}?page=1"
    pages = {
        CALGARY_CATALOG_URL: _calgary_card(
            "Anthropology - MA - Thesis", "Master of Arts", "/anthropology"
        )
        + f'<li class="pager__item--next"><a href="{second_url}">Next</a></li>',
        second_url: _calgary_card("Anthropology - PhD", "Doctor of Philosophy", "/phd"),
        CALGARY_APPLICATION_URL: (
            "Review the application deadlines for your graduate program."
        ),
    }

    rows = (
        CalgaryAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Anthropology (Thesis)", "Master of Arts")
    ]


def test_tufts_follows_infinite_scroll_pages_and_keeps_masters() -> None:
    second_url = f"{TUFTS_CATALOG_URL}?page=1"
    pages = {
        TUFTS_CATALOG_URL: _tufts_card("Art Education - Master's", "Master's", "/art")
        + f'<a rel="next" href="{second_url}">See More Programs</a>',
        second_url: _tufts_card("Biology - Doctorate", "Doctorate", "/biology"),
        TUFTS_APPLICATION_URL: (
            "Review the requirements at each of our graduate schools."
        ),
    }

    rows = (
        TuftsAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Art Education", "Master")
    ]


def test_ucsc_reads_current_catalog_master_list() -> None:
    html = """
      <div id="main"><h1>Master's Degrees</h1><div class="combinedChild"></div><ul>
        <li><a href="/applied">Applied Mathematics M.S.</a></li>
        <li><a href="/art">Environmental Art and Social Practice M.F.A.</a></li>
        <li><a href="/phd">Chemistry Ph.D.</a></li>
      </ul></div>
    """

    rows = UCSCAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Applied Mathematics", "M.S."),
        ("Environmental Art and Social Practice", "M.F.A."),
    ]


def _twente_card(name: str, degree: str, href: str) -> str:
    return f"""
      <a class="studyfinder__programme__link" href="{href}">
        <span class="studyfinder__programme__title__text">{name}</span>
        <div class="studyfinder__programme__metadata"><span class="degree">{degree}</span></div>
      </a>
    """


def _twente_deadlines() -> str:
    return """
    <main><h1>What deadline applies to me?</h1>
      <section class="wh-form__richtext">
        <b>Students with an EEA nationality (non-Dutch)</b>
        <table><tr><td></td><td>September intake</td><td>February intake</td></tr>
          <tr><td>You can start your application from</td><td>1 October</td><td>1 March</td></tr>
          <tr><td>Deadline completed application with all required uploads</td><td>before 1 July</td><td>before 1 December</td></tr>
        </table>
      </section>
      <section class="wh-form__richtext">
        <b>Students with a non-EEA (visa) nationality</b>
        <table><tr><td></td><td>September intake</td><td>February intake</td></tr>
          <tr><td>You can start your application from</td><td>1 October</td><td>1 March</td></tr>
          <tr><td>Deadline completed application with all required uploads</td><td>before 1 May</td><td>before 1 October</td></tr>
        </table>
      </section>
    </main>
    """


def _leicester_card(name: str, href: str) -> str:
    return f'<h4 class="search-result-list__title"><a href="{href}">{name}</a></h4>'


def _calgary_card(name: str, credential: str, href: str) -> str:
    return f"""
      <div class="row results"><div class="result"><div class="result-content">
        <p class="credential">{credential}</p><p class="program"><a href="{href}">{name}</a></p>
      </div></div></div>
    """


def _tufts_card(name: str, degree: str, href: str) -> str:
    return f"""
      <article class="node--type-program"><h4 class="program--title">{name}</h4>
        <div class="program--degree">{degree}</div><a class="program--cta" href="{href}"></a>
      </article>
    """
