from __future__ import annotations

import pytest

from gradwindow.programme_adapters.base import OfficialSourceTransportError
from gradwindow.programme_adapters.charite import ChariteAdapter
from gradwindow.programme_adapters.macau import (
    MacauAdapter,
    parse_official_chinese_translations,
)
from gradwindow.programme_adapters.meduni_vienna import (
    ADMISSION_PERIODS_URL,
    MEDICAL_INFORMATICS_URL,
    MOLECULAR_PRECISION_MEDICINE_URL,
    PSYCHOTHERAPY_URL,
    MedUniViennaAdapter,
)
from gradwindow.programme_adapters.uab import UABAdapter
from gradwindow.programme_adapters.weizmann import WeizmannAdapter


def test_macau_reads_programmes_and_two_official_application_batches() -> None:
    html = """
      <p>Academic Year 2027/2028</p>
      <table>
        <tr><th>Academic Year 2027/2028</th><th>Application Period</th></tr>
        <tr><td>Master's degree programmes</td><td>
          3 August 2026 – 3 December 2026 (1st batch)
          4 December 2026 – 30 April 2027 (2nd batch)</td></tr>
      </table>
      <table><tr><td>Faculty of Science</td><td><p>Master of Science</p><ul>
        <li><a href="https://science.um.edu.mo/data/">Data Science</a></li>
      </ul></td></tr></table>
    """

    programme = (
        MacauAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes[0]
    )

    assert (programme.name, programme.degree_type) == (
        "Data Science",
        "Master of Science",
    )
    assert [
        (window.opens_at, window.closes_at, window.round, window.opens_at_basis)
        for window in programme.windows
    ] == [
        ("2026-08-03", "2026-12-03", "1st batch", "official"),
        ("2026-12-04", "2027-04-30", "2nd batch", "official"),
    ]


def test_macau_matches_official_chinese_labels_by_mirrored_catalogue_order() -> None:
    english = """
      <table><tr><td>Faculty</td><td><p>Master of Science</p><ul>
        <li><a href="https://science.um.edu.mo/data/">Data Science</a></li>
      </ul>
      <a href="https://arts.um.edu.mo/fine-arts/">Master of Fine Arts</a>
      </td></tr>
      <tr><td>Education</td><td><p>Postgraduate Certificate</p><ul>
        <li><a href="https://education.um.edu.mo/pre-primary/">Pre-Primary Education</a></li>
      </ul>
      <a href="https://education.um.edu.mo/tesol/">Master of Arts in TESOL</a>
      </td></tr></table>
    """
    chinese = """
      <table><tr><td>學院</td><td><p>理學碩士</p><ul>
        <li><a href="https://science.um.edu.mo/zh-hant/data/">數據科學</a></li>
      </ul>
      <a href="https://arts.um.edu.mo/zh-hant/fine-arts/">藝術碩士學位</a>
      </td></tr>
      <tr><td>教育學院</td><td><p>學士後證書</p><ul>
        <li><a href="https://education.um.edu.mo/zh-hant/pre-primary/">幼兒教育</a></li>
      </ul>
      <a href="https://education.um.edu.mo/zh-hant/tesol/">文學碩士學位（英語教學）</a>
      </td></tr></table>
    """

    assert parse_official_chinese_translations(english, chinese) == {
        "macau-data-science-master-of-science": "數據科學",
        "macau-master-of-arts-in-tesol-master": "文學碩士學位（英語教學）",
        "macau-master-of-fine-arts-master": "藝術碩士學位",
    }


def test_weizmann_reads_the_five_named_msc_fields() -> None:
    html = "".join(
        f'<h3 class="field-of-study-wrapper">{name}</h3>'
        for name in [
            "Physics",
            "Chemistry",
            "Math &amp; CS",
            "Science Teaching",
            "Life Sciences",
        ]
    )

    rows = WeizmannAdapter().parse_catalog(html).programmes

    assert len(rows) == 5
    assert rows[0].degree_type == "MSc"


def test_meduni_vienna_uses_canonical_pages_and_parses_exact_windows() -> None:
    assert MOLECULAR_PRECISION_MEDICINE_URL.startswith("https://www.meduniwien.ac.at/")
    pages = {
        MEDICAL_INFORMATICS_URL: """
          <h1>Master’s Programme in Medical Informatics at MedUni Vienna</h1>
          <h2>Online Application</h2>
        """,
        ADMISSION_PERIODS_URL: """
          <h1>Admission Periods</h1>
          <h2>Summer semester 2026</h2>
          <p>07 January 2026 - 05 February 2026 | General admission period</p>
          <h2>Winter semester 2026/27</h2>
          <p>06 July 2026 - 05 September 2026 | General admission period</p>
          <p>06 September 2026 - 31 October 2026 | Exception period</p>
          <h2>Summer semester 2027</h2>
          <p>08 January 2027 - 05 February 2027 | General admission period</p>
        """,
        MOLECULAR_PRECISION_MEDICINE_URL: """
          <nav>Application &amp; Admission Student Exchange Campus</nav>
          <h1>The Molecular Precision Medicine Master’s Programme</h1>
          <p>Application &amp; Admission</p>
          <p>Application 1 <sup>st</sup> March - 31 <sup>st</sup> March 2026</p>
          <p>Start in winter semester</p>
        """,
        PSYCHOTHERAPY_URL: """
          <h1>Masterstudium Psychotherapie</h1>
          <p>Im Oktober 2026 startet das neue Masterstudium Psychotherapie.</p>
          <p>Antragsfrist für das Studienjahr 2026/27:
             2. März bis 7. April 2026</p>
        """,
    }
    fetched: list[str] = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        return pages[url]

    rows = MedUniViennaAdapter().parse_catalog_from_fetcher(fetcher).programmes

    assert fetched == [
        MEDICAL_INFORMATICS_URL,
        MOLECULAR_PRECISION_MEDICINE_URL,
        PSYCHOTHERAPY_URL,
        ADMISSION_PERIODS_URL,
    ]
    assert [row.name for row in rows] == [
        "Medical Informatics",
        "Molecular Precision Medicine",
        "Psychotherapy",
    ]
    medical_informatics, precision_medicine, psychotherapy = rows
    assert [
        (
            window.round,
            window.intake,
            window.opens_at,
            window.closes_at,
        )
        for window in medical_informatics.windows
    ] == [
        (
            "General admission period",
            "Winter semester 2026/27",
            "2026-07-06",
            "2026-09-05",
        ),
        (
            "General admission period",
            "Summer semester 2027",
            "2027-01-08",
            "2027-02-05",
        ),
    ]
    assert "not a selective programme application period" in (
        medical_informatics.deadline_text
    )
    assert [
        (
            window.intake,
            window.opens_at,
            window.closes_at,
            window.opens_at_basis,
        )
        for window in precision_medicine.windows
    ] == [("Winter semester 2026", "2026-03-01", "2026-03-31", "official")]
    assert [
        (
            window.intake,
            window.opens_at,
            window.closes_at,
            window.opens_at_basis,
        )
        for window in psychotherapy.windows
    ] == [("Academic year 2026/27", "2026-03-02", "2026-04-07", "official")]


def test_meduni_vienna_fails_when_a_canonical_catalogue_source_is_unavailable() -> None:
    pages = {
        MEDICAL_INFORMATICS_URL: "Master’s Programme in Medical Informatics",
        MOLECULAR_PRECISION_MEDICINE_URL: (
            "Molecular Precision Medicine 1 March - 31 March 2026"
        ),
    }

    with pytest.raises(OfficialSourceTransportError, match="Psychotherapy"):
        MedUniViennaAdapter().parse_catalog_from_fetcher(pages.__getitem__)


def test_meduni_vienna_ignores_unrelated_page_dates_outside_application_section() -> (
    None
):
    pages = {
        MEDICAL_INFORMATICS_URL: "Master’s Programme in Medical Informatics",
        ADMISSION_PERIODS_URL: """
          <h1>Admission Periods</h1>
          <h2>Winter semester 2026/27</h2>
          <p>06 July 2026 - 05 September 2026 | General admission period</p>
          <h2>Summer semester 2027</h2>
          <p>08 January 2027 - 05 February 2027 | General admission period</p>
        """,
        MOLECULAR_PRECISION_MEDICINE_URL: """
          <h1>The Molecular Precision Medicine Master’s Programme</h1>
          <p>Application &amp; Admission</p><p>Application details will follow.</p>
          <h2>Language of Instruction</h2><p>English B2</p>
          <h2>Legal basis</h2><a>Curriculum revision 5 December 2025</a>
        """,
        PSYCHOTHERAPY_URL: """
          <h1>Masterstudium Psychotherapie</h1>
          <p>Antragsfrist für das Studienjahr 2026/27:
             2. März bis 7. April 2026</p>
        """,
    }

    catalog = MedUniViennaAdapter().parse_catalog_from_fetcher(pages.__getitem__)

    precision = next(
        item
        for item in catalog.programmes
        if item.name == "Molecular Precision Medicine"
    )
    assert precision.windows == []


def test_meduni_vienna_watch_content_ignores_unrelated_page_dates() -> None:
    adapter = MedUniViennaAdapter()
    first = """
      <article>
        <div class="program__item">
          <h2 class="program__title">Application &amp; Admission</h2>
          <p>Application 1 March - 31 March 2026</p>
        </div>
        <h2>Curriculum</h2><p>Revised 5 December 2025</p>
      </article>
    """
    second = first.replace("5 December 2025", "8 January 2026")

    assert adapter.window_watch_content(
        MOLECULAR_PRECISION_MEDICINE_URL, first
    ) == adapter.window_watch_content(MOLECULAR_PRECISION_MEDICINE_URL, second)
    assert adapter.window_watch_content(
        MOLECULAR_PRECISION_MEDICINE_URL, first
    ) != adapter.window_watch_content(
        MOLECULAR_PRECISION_MEDICINE_URL,
        first.replace("31 March 2026", "30 March 2026"),
    )


def test_charite_excludes_programmes_closed_to_enrolment() -> None:
    html = """
      <main>
        <a title="Public Health*" href="https://bsph.charite.de/public-health/">
          <strong>Public Health</strong><p>Master of Science programme</p></a>
        <a class="section-teaser" title="Old Public Health" href="/old/">
          Old master's programme</a>
      </main>
    """

    rows = ChariteAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [("Public Health", "MSc")]


def test_uab_reads_master_awards_and_excludes_md_only_rows() -> None:
    html = """
      <table><tr><td><a href="/biology/">Biology (M.S., Ph.D.)</a></td>
        <td><a href="/medicine/">Medicine (M.D.)</a></td></tr></table>
    """

    rows = UABAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [("Biology", "M.S.")]
