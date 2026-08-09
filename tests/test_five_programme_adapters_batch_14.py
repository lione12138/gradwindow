from __future__ import annotations

from gradwindow.programme_adapters.cape_town import CapeTownAdapter
from gradwindow.programme_adapters.cardiff import CardiffAdapter
from gradwindow.programme_adapters.michigan_state import MichiganStateAdapter
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


def test_michigan_state_records_client_rendered_directory() -> None:
    html = '<title>Majors, degrees and programs</title>{"ProgramList": {}}'
    row = MichiganStateAdapter().parse_catalog(html).programmes[0]
    assert row.id == "msu-graduate-programmes"
    assert row.parse_status == "no-deadline"


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
