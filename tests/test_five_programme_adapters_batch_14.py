from __future__ import annotations

import pytest

from gradwindow.programme_adapters.base import OfficialSourceTransportError
from gradwindow.programme_adapters.cape_town import CapeTownAdapter
from gradwindow.programme_adapters.cardiff import CardiffAdapter
from gradwindow.programme_adapters.michigan_state import (
    CATALOG_URL,
    REGISTRAR_CATALOG_URLS,
    MichiganStateAdapter,
)
from gradwindow.programme_adapters.nycu import NYCUAdapter
from gradwindow.programme_adapters.tu_dresden import TUDresdenAdapter


def test_nycu_reads_spring_master_routes_and_one_shared_exact_window() -> None:
    adapter = NYCUAdapter(
        minimum_expected_programmes=2,
        pdf_text_fetcher=lambda url: _nycu_guide(),
    )
    page = '<a href="https://drive.google.com/file/d/guide/view">Spring 2027 '
    page += "Admission Guidelines for International Degree Students</a>"
    rows = adapter.parse_catalog_from_fetcher(lambda url: page).programmes
    assert [row.name for row in rows] == [
        "Institute of Biomedical Informatics",
        "Institute of Intelligent Systems",
        "International degree-seeking programmes",
    ]
    assert rows[0].windows == []
    assert rows[-1].windows[0].opens_at == "2026-08-10"
    assert rows[-1].windows[0].closes_at == "2026-09-30"


def test_cardiff_records_cloudflare_catalogue_limitation() -> None:
    row = CardiffAdapter().parse_catalog("Cardiff University Blogs").programmes[0]
    assert row.id == "cardiff-postgraduate-taught-programmes"
    assert row.parse_status == "no-deadline"


def test_michigan_state_reads_registrar_master_degree_catalogue() -> None:
    html = """
    <h2>Graduate Degrees</h2>
    <h3>College of Engineering</h3>
    <h4>Computer Science and Engineering</h4>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=COMPSC_MS">
      Computer Science - Master of Science (MS)
    </a>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=COMPSC_PHD">
      Computer Science - Doctor of Philosophy (PHD)
    </a>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=EDUC_MAT">
      Teaching and Curriculum - Master of Arts for Teachers (M.A.T.)
    </a>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=FUTURE_XYZ">
      Future Graduate Route (XYZ)
    </a>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=ECO_DUAL">
      Ecology, Evolution, and Behavior - Dual Major (DUAL)
    </a>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=SCHOOL_EDS">
      School Psychology - Educational Specialist (EDS)
    </a>
    <h3>Eli Broad College of Business</h3>
    <h4>Accounting and Information Systems</h4>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=ACCOUNT_MS">
      Accounting - Master of Science (MS)
    </a>
    <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=INDMATH_MS">
      Industrial Mathematics - Master of Science
      (this program is in moratorium effective Fall 2026 through Summer 2027) (MS)
    </a>
    """
    adapter = MichiganStateAdapter(minimum_expected_programmes=4)
    catalog = adapter.parse_catalog(html)
    rows = catalog.programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Accounting", "MS"),
        ("Computer Science", "MS"),
        ("Industrial Mathematics", "MS"),
        ("Teaching and Curriculum", "MAT"),
    ]
    assert rows[0].faculty == "Eli Broad College of Business"
    assert rows[0].department == "Accounting and Information Systems"
    assert "Program=ACCOUNT_MS" in rows[0].source_url
    assert all(row.parse_status == "no-deadline" for row in rows)
    assert adapter.catalogue_granularity == "programme-level"
    assert catalog.diagnostics == {
        "observedGraduateDegreeCodes": [
            "DUAL",
            "EDS",
            "MAT",
            "MS",
            "PHD",
            "XYZ",
        ],
        "unknownGraduateDegreeCodes": ["XYZ"],
    }
    assert catalog.warnings[0]["reason"] == "UNKNOWN_DEGREE_CODE"
    assert catalog.warnings[0]["unknownDegreeCodes"] == ["XYZ"]
    paused = next(row for row in rows if row.name == "Industrial Mathematics")
    assert paused.admission_status == "paused"
    assert paused.moratorium_from == "Fall 2026"
    assert paused.moratorium_to == "Summer 2027"
    assert "moratorium" in paused.deadline_text


def test_michigan_state_tries_alternative_registrar_entries() -> None:
    catalogue = """
      <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=EDUC_MAT">
        Teaching and Curriculum - Master of Arts for Teachers (M.A.T.)
      </a>
    """
    fetched: list[str] = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        if url == CATALOG_URL:
            return "Request unsuccessful. Incapsula incident ID."
        return catalogue

    result = MichiganStateAdapter(
        minimum_expected_programmes=1,
        browser_content_fetcher=lambda _url: "",
    ).parse_catalog_from_fetcher(fetcher)

    assert fetched == list(REGISTRAR_CATALOG_URLS[:2])
    assert [item.name for item in result.programmes] == ["Teaching and Curriculum"]
    assert (
        result.programmes[0].retrieval_method == "official-registrar-graduate-degrees"
    )


def test_michigan_state_classifies_incapsula_as_transport_failure() -> None:
    adapter = MichiganStateAdapter(
        minimum_expected_programmes=1,
        browser_content_fetcher=lambda _url: (_ for _ in ()).throw(
            RuntimeError("browser quota unavailable")
        ),
    )

    with pytest.raises(OfficialSourceTransportError, match="Browser Rendering"):
        adapter.parse_catalog_from_fetcher(
            lambda _url: '<script src="/_Incapsula_Resource"></script>'
        )


def test_michigan_state_uses_browser_rendering_for_access_challenge() -> None:
    catalogue = """
      <a href="ProgramDetail.aspx?PType=GRADLAWM&amp;Program=EDUC_MAT">
        Teaching and Curriculum - Master of Arts for Teachers (M.A.T.)
      </a>
    """
    adapter = MichiganStateAdapter(
        minimum_expected_programmes=1,
        browser_content_fetcher=lambda _url: catalogue,
    )

    result = adapter.parse_catalog_from_fetcher(
        lambda _url: "Request unsuccessful. Incapsula incident ID."
    )

    assert [item.degree_type for item in result.programmes] == ["MAT"]
    assert result.programmes[0].retrieval_method == "cloudflare-browser-rendering"


def test_michigan_state_uses_complete_official_admissions_fallback() -> None:
    fallback = """
      <div id="gradwindow-msu-programmes" data-complete="true">
        <a class="program-wrapper" href="https://engineering.msu.edu/chem-ms">
          <p class="pre-header">Master's degree</p>
          <p class="h2">Chemical Engineering</p>
          <p class="collegeName">College of Engineering</p>
        </a>
        <a class="program-wrapper" href="https://education.msu.edu/teaching-ma">
          <p class="pre-header">Master's degree</p>
          <p class="h2">Teaching and Curriculum</p>
          <p class="collegeName">College of Education</p>
        </a>
      </div>
    """

    def browser_fetcher(url: str) -> str:
        return fallback if "admissions.msu.edu" in url else "Request unsuccessful"

    adapter = MichiganStateAdapter(
        minimum_expected_programmes=2,
        browser_content_fetcher=browser_fetcher,
    )
    result = adapter.parse_catalog_from_fetcher(
        lambda _url: "Request unsuccessful. Incapsula incident ID."
    )

    assert [item.name for item in result.programmes] == [
        "Chemical Engineering",
        "Teaching and Curriculum",
    ]
    assert adapter.catalogue_status == "partial"
    assert result.warnings[0]["reason"] == "FALLBACK_CATALOGUE_IDENTITY"


def test_cape_town_reads_official_faculty_handbook_programmes() -> None:
    adapter = CapeTownAdapter(
        minimum_expected_programmes=2,
        pdf_text_fetcher=lambda url: (
            "Master of Engineering in Water Quality"
            " ........................................ 42\n"
            "MSc/MPhil SM001/2 CSC05 Computer Science\n"
        ),
    )
    links = "".join(
        f'<a href="/files/{marker}.pdf">Postgraduate</a>'
        for marker in (
            "commerce-handbook-6b",
            "ebe-handbook-7b",
            "fhs-handbook-8b",
            "hum-handbook-9b",
            "law-handbook-10",
            "sci-handbook-11",
        )
    )
    rows = adapter.parse_catalog_from_fetcher(lambda url: links).programmes
    assert {row.name for row in rows} == {
        "Master of Engineering in Water Quality",
        "MSc/MPhil in Computer Science",
    }
    assert {row.faculty for row in rows} >= {"Commerce", "Science"}
    assert next(row for row in rows if "Computer Science" in row.name).id == (
        "uct-masters-computer-science"
    )


def test_tu_dresden_reads_master_cards_from_sins_results() -> None:
    html = """
      <a href="https://tu-dresden.de/sins/27"><div class="teaser-content">
        <span class="fieldcolor">Master</span><h2>ACCESS</h2>
      </div></a>
      <a href="https://tu-dresden.de/sins/73"><div class="teaser-content">
        <span class="fieldcolor">Master</span><h2>Computer Science</h2>
      </div></a>
    """
    adapter = TUDresdenAdapter(minimum_expected_programmes=2)
    rows = adapter.parse_catalog(html).programmes
    assert [row.name for row in rows] == ["ACCESS", "Computer Science"]
    assert all(row.windows == [] for row in rows)


def _nycu_guide() -> str:
    first = """
      Application Procedure
      Online application system starts August 10, 2026
      Online application deadline AM11:59, September 30, 2026
    """
    biomedical = """
      28
      College of Medicine
      Institute of Biomedical Informatics
      Intake Degree Program Group Language of Instruction
      Spring Master English-taught Program
      Application Regulations
    """
    intelligent = """
      184
      College of Artificial Intelligence
      Institute of Intelligent Systems
      Intake Degree Program Group Language of Instruction
      Spring Master English-taught Program
      Application Regulations
    """
    return "\f".join((first, biomedical, intelligent))
