from __future__ import annotations

from gradwindow.programme_adapters.charite import ChariteAdapter
from gradwindow.programme_adapters.macau import (
    MacauAdapter,
    parse_official_chinese_translations,
)
from gradwindow.programme_adapters.meduni_vienna import MedUniViennaAdapter
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


def test_meduni_vienna_prefers_current_medical_informatics_link() -> None:
    html = """
      <a href="/old/">Medical Informatics Master - old</a>
      <a href="/new/">Medical Informatics Master - new</a>
      <a href="/precision/">Molecular Precision Medicine Master’s Programme</a>
      <a href="/psychotherapy/">Masterstudium Psychotherapie</a>
    """

    rows = MedUniViennaAdapter().parse_catalog(html).programmes

    assert len(rows) == 3
    medical_informatics = next(row for row in rows if row.name == "Medical Informatics")
    assert medical_informatics.source_url.endswith("/new/")


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
