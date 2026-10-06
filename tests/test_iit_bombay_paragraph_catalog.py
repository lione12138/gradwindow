from html import escape

import pytest

from gradwindow.programme_adapters.iit_bombay import (
    CATALOG_URL,
    IITBombayAdapter,
)

# Reduced official paragraph layout, captured 2026-10-06. Include all uncoded
# rows because their department boundaries no longer have HTML semantics.
SECTIONS = [
    (
        "Master of Technology/(Dual Degree) Master of Technology + Doctor of Philosophy",
        ["(AE1) Aerodynamics", "(AE2) Dynamics & Control", "Aerospace Engineering"],
    ),
    (
        "Master of Design (M.Des.) and Master of Design by Research (M.Des. by Research)",
        ["(AN) Animation Design", "IDC School of Design"],
    ),
    (
        "Master of Business Administration",
        ["(MBA) Master of Business Administration", "School of Management (SJMSOM)"],
    ),
    (
        "Master of Business Administration (Executive)",
        ["(EMBA) Master of Business Administration", "School of Management (SJMSOM)"],
    ),
    (
        "MA+Ph.D. (Dual Degree) in Philosophy",
        ["MA+Ph.D. (Dual Degree) in Philosophy", "Humanities and Social Sciences"],
    ),
    (
        "Master of Arts by Research (MA.Res.)",
        ["Master of Arts by Research (MA.Res.)", "Humanities and Social Sciences"],
    ),
    ("Master in Public Policy", ["Public Policy", "Centre for Policy Studies"]),
    (
        "Master of Science",
        [
            "Applied Geology",
            "Applied Geophysics",
            "Earth Sciences",
            "Applied Statistics & Informatics",
            "Mathematics",
            "Biotechnology",
            "Biosciences & Bioengineering",
            "Chemistry",
            "Chemistry",
            "Operations Research",
            "Industrial Engineering and Operations Research",
            "Physics",
            "Physics",
        ],
    ),
    (
        "(Dual Degree) Master of Science + Doctor of Philosophy",
        [
            "Environmental Science",
            "Department of Environmental Science & Engineering",
            "Energy",
            "Energy Science and Engineering",
        ],
    ),
    (
        "Master in Development Practice (MDP)",
        [
            "Master in Development Practice",
            "Centre for Technology Alternatives for Rural Areas (CTARA)",
        ],
    ),
]


def page(sections=SECTIONS):
    paragraphs = ["Postgraduate Programmes at IIT Bombay"]
    for heading, rows in sections:
        paragraphs.extend([heading, "Degree/Specialization", "Department", *rows])
    return (
        '<div class="field--name-body">'
        + "".join(f"<p>{escape(value)}</p><p>&nbsp;</p>" for value in paragraphs)
        + "</div>"
    )


def test_flattened_catalogue_retains_degrees_and_shared_departments():
    adapter = IITBombayAdapter()
    adapter.minimum_expected_programmes = 1
    programmes = adapter.parse_catalog(page()).programmes
    pairs = {(item.name, item.degree_type) for item in programmes}
    assert len(programmes) == 18
    assert ("Aerodynamics", "M.Tech") in pairs
    assert ("Dynamics & Control", "M.Tech") in pairs
    assert ("Executive Master of Business Administration", "EMBA") in pairs
    assert ("Master of Business Administration", "MBA") in pairs
    assert ("Applied Geology", "MSc") in pairs
    assert ("Applied Geophysics", "MSc") in pairs
    assert ("Chemistry", "MSc") in pairs
    assert not any(
        name in {"Earth Sciences", "Mathematics", "Aerospace Engineering"}
        for name, _ in pairs
    )
    assert all(
        item.source_url == CATALOG_URL and not item.windows for item in programmes
    )


@pytest.mark.parametrize(
    "html",
    [
        page(SECTIONS[:-1]),
        page(SECTIONS + [SECTIONS[0]]),
        page().replace("Master in Public Policy", "Unknown Degree"),
        page().replace("Applied Geology", "Changed Geology"),
        page().replace("(AN) Animation Design", "Animation Design"),
        "<div><p>Master of Science</p></div>",
    ],
)
def test_changed_or_partial_flattened_catalogue_fails_closed(html):
    with pytest.raises(ValueError, match="IIT Bombay"):
        IITBombayAdapter().extract_entries(html)


def test_sections_are_matched_by_heading_not_position():
    adapter = IITBombayAdapter()
    assert {
        (item.name, item.degree_type)
        for item in adapter.extract_entries(page(list(reversed(SECTIONS))))
    } == {(item.name, item.degree_type) for item in adapter.extract_entries(page())}
