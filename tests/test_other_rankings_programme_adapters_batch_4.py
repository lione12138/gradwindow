from __future__ import annotations

from datetime import date

from gradwindow.programme_adapters.florida import FloridaAdapter
from gradwindow.programme_adapters.gottingen import (
    ADMISSIONS_URL as GOTTINGEN_ADMISSIONS_URL,
)
from gradwindow.programme_adapters.gottingen import CATALOG_URL as GOTTINGEN_CATALOG_URL
from gradwindow.programme_adapters.gottingen import GottingenAdapter
from gradwindow.programme_adapters.hamburg import (
    ADMISSIONS_URL as HAMBURG_ADMISSIONS_URL,
)
from gradwindow.programme_adapters.hamburg import CATALOG_ASSET_URL, HamburgAdapter
from gradwindow.programme_adapters.hamburg import CATALOG_URL as HAMBURG_CATALOG_URL
from gradwindow.programme_adapters.tubingen import (
    ADMISSIONS_URL as TUBINGEN_ADMISSIONS_URL,
)
from gradwindow.programme_adapters.tubingen import CATALOG_URL as TUBINGEN_CATALOG_URL
from gradwindow.programme_adapters.tubingen import TubingenAdapter
from gradwindow.programme_adapters.uci import CATALOG_URL as UCI_CATALOG_URL
from gradwindow.programme_adapters.uci import RESULTS_URL, UCIAdapter


def test_tubingen_follows_catalogue_pagination_and_keeps_masters() -> None:
    second_url = (
        f"{TUBINGEN_CATALOG_URL}?"
        "tx_in2utcourses_list%5BcoursesPaginator%5D%5BcurrentPage%5D=2"
    )
    pages = {
        TUBINGEN_CATALOG_URL: _tubingen_box(
            "Accounting and Finance", "Master", "accounting-master"
        )
        + f'<a href="{second_url}">Next</a>',
        second_url: _tubingen_box(
            "Advanced Quantum Physics", "Master", "quantum-master"
        )
        + _tubingen_box("Biology", "Bachelor", "biology-bachelor"),
        TUBINGEN_ADMISSIONS_URL: "There are different application deadlines.",
    }

    rows = (
        TubingenAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [row.name for row in rows] == [
        "Accounting and Finance",
        "Advanced Quantum Physics",
    ]
    assert all(row.degree_type == "Master" for row in rows)


def test_uci_reads_master_cards_and_keeps_only_current_deadline_guidance() -> None:
    pages = {
        UCI_CATALOG_URL: "<script>degree_program</script>",
        RESULTS_URL: (
            _uci_card("Art History", "Master's", "February 15, 2027")
            + _uci_card("Asian American Studies", "Master's", "February 11, 2026")
            + _uci_card("Anthropology", "PhD", "December 1, 2027")
        ),
    }

    rows = (
        UCIAdapter(
            minimum_expected_programmes=2,
            reference_date=date(2026, 8, 10),
        )
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [row.name for row in rows] == ["Art History", "Asian American Studies"]
    assert rows[0].windows[0].closes_at == "2027-02-15"
    assert rows[0].windows[0].opens_at is None
    assert rows[1].windows == []


def test_hamburg_reads_official_javascript_catalogue_asset() -> None:
    asset = """
      <table id="studiengaenge"><tbody>
        <tr><td><a href="studienangebot/studiengang.html?1">Chemistry Master of Science</a></td>
          <td>M.Sc.</td><td>MIN</td><td></td><td>WiSe</td><td>ENG</td></tr>
        <tr><td><a href="studienangebot/studiengang.html?2">History Bachelor of Arts</a></td>
          <td>B.A.</td><td>GW</td><td></td><td>WiSe</td><td>GER</td></tr>
        <tr><td><a href="studienangebot/studiengang.html?3">Wood Science Master of Science</a></td>
          <td>M.Sc.</td><td>MIN</td><td></td><td>expires</td><td>ENG</td></tr>
      </tbody></table>
    """
    pages = {
        HAMBURG_CATALOG_URL: '<script src="studiengaenge/indexEN.js"></script>',
        CATALOG_ASSET_URL: asset,
        HAMBURG_ADMISSIONS_URL: "Master application information",
    }

    rows = (
        HamburgAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [row.name for row in rows] == ["Chemistry"]
    assert rows[0].degree_type == "M.Sc."
    assert rows[0].source_url.endswith("studienangebot/studiengang.html?1")


def test_gottingen_reads_master_routes_from_official_a_to_z() -> None:
    pages = {
        GOTTINGEN_CATALOG_URL: """
          <main>
            <a href="/en/1.html">Agribusiness (MBA)</a>
            <a href="/en/2.html">Applied Computer Science (M.Sc.)</a>
            <a href="/en/3.html">Agricultural Sciences (B.Sc.)</a>
            <a href="/en/4.html">Alias: refer to Applied Statistics (M.Sc.)</a>
          </main>
        """,
        GOTTINGEN_ADMISSIONS_URL: (
            "The application procedures and applications deadlines vary from "
            "faculty to faculty."
        ),
    }

    rows = (
        GottingenAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [row.name for row in rows] == ["Agribusiness", "Applied Computer Science"]
    assert [row.degree_type for row in rows] == ["MBA", "M.Sc."]


def test_florida_reads_top_level_majors_without_concentrations() -> None:
    html = """
      <h3>Master of Arts (M.A.) <sup>T/N</sup></h3>
      <ul>
        <li>Anthropology <sup>T/N</sup><ul><li>Historic Preservation</li></ul></li>
        <li>Art History <sup>T</sup></li>
      </ul>
      <h3>Doctor of Philosophy (Ph.D.)</h3><ul><li>Anthropology</li></ul>
    """

    rows = FloridaAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [row.name for row in rows] == ["Anthropology", "Art History"]
    assert all(row.degree_type == "Master of Arts (M.A.)" for row in rows)


def _tubingen_box(name: str, degree: str, slug: str) -> str:
    return f"""
      <div class="ut-box"><div class="ut-box__block"><h3>{name}</h3>
        <div class="ut-box__text"><p><strong>Degree</strong><br>{degree}</p>
          <a title="{name}" href="/en/study/finding-a-course/degree-programs-available/detail/course/{slug}/">Details</a>
        </div></div></div>
    """


def _uci_card(name: str, degree: str, deadline: str) -> str:
    slug = name.casefold().replace(" ", "-")
    return f"""
      <div class="card">
        <td class="card-title">{name}<div class="degree_button">{degree}</div></td>
        <td class="details-cell"><a href="https://grad.uci.edu/{slug}">Details</a></td>
        <td><strong>Application Deadline:</strong> {deadline}</td>
      </div>
    """
