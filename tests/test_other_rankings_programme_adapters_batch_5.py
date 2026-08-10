from __future__ import annotations

from gradwindow.programme_adapters.case_western import (
    APPLICATION_URL as CASE_APPLICATION_URL,
)
from gradwindow.programme_adapters.case_western import CATALOG_URL as CASE_CATALOG_URL
from gradwindow.programme_adapters.case_western import CaseWesternAdapter
from gradwindow.programme_adapters.dartmouth import (
    APPLICATION_URL as DARTMOUTH_APPLICATION_URL,
)
from gradwindow.programme_adapters.dartmouth import (
    CATALOG_URL as DARTMOUTH_CATALOG_URL,
)
from gradwindow.programme_adapters.dartmouth import DartmouthAdapter
from gradwindow.programme_adapters.maastricht import (
    APPLICATION_URL as MAASTRICHT_APPLICATION_URL,
)
from gradwindow.programme_adapters.maastricht import (
    CATALOG_URL as MAASTRICHT_CATALOG_URL,
)
from gradwindow.programme_adapters.maastricht import MaastrichtAdapter
from gradwindow.programme_adapters.radboud import (
    APPLICATION_URL as RADBOUD_APPLICATION_URL,
)
from gradwindow.programme_adapters.radboud import CATALOG_URL as RADBOUD_CATALOG_URL
from gradwindow.programme_adapters.radboud import RadboudAdapter
from gradwindow.programme_adapters.rochester import (
    APPLICATION_URL as ROCHESTER_APPLICATION_URL,
)
from gradwindow.programme_adapters.rochester import (
    CATALOG_URL as ROCHESTER_CATALOG_URL,
)
from gradwindow.programme_adapters.rochester import RochesterAdapter


def test_maastricht_follows_pagination_and_reads_official_cards() -> None:
    second_url = f"{MAASTRICHT_CATALOG_URL}?page=1"
    pages = {
        MAASTRICHT_CATALOG_URL: _maastricht_card("Data Science", "/data-science")
        + f'<a rel="next" href="{second_url}">Next</a>',
        second_url: _maastricht_card("European Law School (LLM)", "/law"),
        MAASTRICHT_APPLICATION_URL: "Admission and enrolment information",
    }

    rows = (
        MaastrichtAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [row.name for row in rows] == ["Data Science", "European Law School (LLM)"]
    assert [row.degree_type for row in rows] == ["Master", "LLM"]


def test_rochester_keeps_master_degrees_from_graduate_rows() -> None:
    pages = {
        ROCHESTER_CATALOG_URL: """
          <p class="research-link grad"><a href="https://rochester.edu/bio">Biology</a>
            <span class="cert">BA, MS, PhD</span></p>
          <p class="research-link grad"><a href="https://rochester.edu/music">Music</a>
            <span class="cert">MA, MM, PhD</span></p>
          <p class="research-link grad"><a href="https://rochester.edu/chem">Chemistry</a>
            <span class="cert">BS, PhD</span></p>
        """,
        ROCHESTER_APPLICATION_URL: (
            "Each of our schools has its own application process for graduate students."
        ),
    }

    rows = (
        RochesterAdapter(minimum_expected_programmes=3)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Biology", "MS"),
        ("Music", "MA"),
        ("Music", "MM"),
    ]


def test_dartmouth_keeps_only_listed_masters_sections() -> None:
    pages = {
        DARTMOUTH_CATALOG_URL: """
          <h2>Master of Fine Arts</h2><div><ul><li><a href="/sonic">Sonic Practice</a></li></ul></div>
          <h2>Master's Programs (MS and MA)</h2><div><ul><li><a href="/computer">Computer Science</a></li></ul></div>
          <h2>Doctoral Programs (PhD)</h2><div><ul><li><a href="/biology">Biology</a></li></ul></div>
        """,
        DARTMOUTH_APPLICATION_URL: "Fall 2027 will open in September.",
    }

    rows = (
        DartmouthAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Computer Science", "Master"),
        ("Sonic Practice", "MFA"),
    ]


def test_case_western_reads_master_degree_links_only() -> None:
    pages = {
        CASE_CATALOG_URL: """
          <table><tr><th>Programs</th><th>Degrees</th></tr>
            <tr><td>Anthropology</td><td><a href="/ma">MA</a>, <a href="/phd">PhD</a></td></tr>
            <tr><td><p>Aerospace Physiology</p><p>Available online</p></td>
              <td><a href="/ms">MS</a>, <a href="/cert">Certificate</a></td></tr>
          </table>
        """,
        CASE_APPLICATION_URL: "Application deadlines vary among departments.",
    }

    rows = (
        CaseWesternAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Aerospace Physiology", "MS"),
        ("Anthropology", "MA"),
    ]


def test_radboud_follows_pagination_without_treating_specialisations_as_programmes() -> (
    None
):
    second_url = f"{RADBOUD_CATALOG_URL}?page=1"
    pages = {
        RADBOUD_CATALOG_URL: _radboud_card("Artificial Intelligence", "/ai")
        + "<h3>Machine Learning specialisation</h3>"
        + f'<a rel="next" href="{second_url}">Next</a>',
        second_url: _radboud_card("Computing Science", "/computing"),
        RADBOUD_APPLICATION_URL: (
            "Students can apply from 1 October onwards for the September intake; "
            "or from 1 May onwards for the February intake. Some programmes use a "
            "placement procedure."
        ),
    }

    rows = (
        RadboudAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [row.name for row in rows] == [
        "Artificial Intelligence",
        "Computing Science",
    ]


def _maastricht_card(name: str, href: str) -> str:
    return f"""
      <article data-component-id="um_corporate:list-item">
        <h2><a href="{href}"><span>{name}</span></a></h2>
      </article>
    """


def _radboud_card(name: str, href: str) -> str:
    return f'<h2 class="card__title"><a href="{href}">{name}</a></h2>'
