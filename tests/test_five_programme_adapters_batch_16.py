from __future__ import annotations

from gradwindow.programme_adapters.hust import (
    CATALOG_URL as HUST_CATALOG_URL,
)
from gradwindow.programme_adapters.hust import HUSTAdapter
from gradwindow.programme_adapters.lausanne import (
    APPLICATION_URL as LAUSANNE_APPLICATION_URL,
)
from gradwindow.programme_adapters.lausanne import LausanneAdapter
from gradwindow.programme_adapters.md_anderson import (
    CATALOG_URL as MD_CATALOG_URL,
)
from gradwindow.programme_adapters.md_anderson import (
    DIAGNOSTIC_URL,
    DOSIMETRY_URL,
    RADIOLOGIC_URL,
    MDAndersonAdapter,
)
from gradwindow.programme_adapters.sichuan import (
    CATALOG_URL as SICHUAN_CATALOG_URL,
)
from gradwindow.programme_adapters.sichuan import GUIDE_URL, SichuanAdapter
from gradwindow.programme_adapters.xjtu import GuidePayload, XJTUAdapter


def test_hust_combines_official_main_and_medical_guides_with_group_window() -> None:
    guide = """
      <p>Application period: October 15, 2025 to March 1, 2026.</p>
      <a href="/2026-MasterPrograms.pdf">Master programs</a>
      <a href="/202610MedicalPrograms.pdf">Medical programs</a>
    """
    master_text = """
      Schools Programs C E A
      School of Materials Science and Engineering
      Materials Science ○ ○ ▷
      School of Integrated Circuits New-Generation Electronic Information
      Technology ○ ▷
    """
    medical_text = """
      同济医院 Tongji Hospital
      内科学 Internal Medicine ○ ◎ ○ ◎
    """

    def pdf_text(url: str) -> str:
        return medical_text if "Medical" in url else master_text

    catalog = HUSTAdapter(
        minimum_expected_programmes=3, pdf_text_fetcher=pdf_text
    ).parse_catalog_from_fetcher(lambda url: guide if url == HUST_CATALOG_URL else "")

    assert [row.name for row in catalog.programmes[:-1]] == [
        "New-Generation Electronic Information Technology",
        "Materials Science",
        "Internal Medicine",
    ]
    window = catalog.programmes[-1].windows[0]
    assert (window.opens_at, window.closes_at) == ("2025-10-15", "2026-03-01")
    assert window.opens_at_basis == "official"


def test_sichuan_preserves_same_named_programmes_in_different_faculties() -> None:
    catalogue = """
      <table>
        <tr><td>1</td><td>硕士研究生</td><td>材料学院 College of Materials</td>
          <td>材料</td><td>汉语</td><td>3</td></tr>
        <tr><td>Master's Degree</td><td>Materials Engineering</td><td>Chinese</td></tr>
        <tr><td>2</td><td>硕士研究生</td><td>工程学院 College of Engineering</td>
          <td>材料</td><td>汉语</td><td>3</td></tr>
        <tr><td>Master's Degree</td><td>Materials Engineering</td><td>Chinese</td></tr>
      </table>
    """
    guide = "<p>Application Period: November 1, 2025 -- May 30, 2026</p>"
    pages = {SICHUAN_CATALOG_URL: catalogue, GUIDE_URL: guide}

    catalog = SichuanAdapter(minimum_expected_programmes=2).parse_catalog_from_fetcher(
        pages.__getitem__
    )

    assert len(catalog.programmes) == 3
    assert len({row.id for row in catalog.programmes}) == 3
    assert catalog.programmes[-1].windows[0].opens_at == "2025-11-01"


def test_xjtu_keeps_exact_closes_as_guidance_when_opening_is_not_exact() -> None:
    payload = GuidePayload(
        text=(
            "Scholarship Program: From now until 17:00 March 31, 2026. "
            "Self-funded Program: From now until 17:00 May 15, 2026."
        ),
        rows=(
            (
                "School of Materials Science and Engineering",
                "Materials Science",
                "Chinese",
                "3",
                "Master of Engineering",
                "Yes",
            ),
            (
                None,
                "and Engineering",
                "English",
                "3",
                "Master of Engineering",
                "Yes",
            ),
            (
                "School of Law",
                "Law",
                "English",
                "2",
                "Master of Laws",
                "No",
            ),
        ),
    )
    catalog = XJTUAdapter(
        minimum_expected_programmes=2, guide_fetcher=lambda _url: payload
    ).parse_catalog_from_fetcher(lambda _url: "")

    assert {row.name for row in catalog.programmes[:-1]} == {
        "Materials Science and Engineering",
        "Law",
    }
    assert [window.closes_at for window in catalog.programmes[-1].windows] == [
        "2026-03-31",
        "2026-05-15",
    ]
    assert all(window.opens_at is None for window in catalog.programmes[-1].windows)


def test_md_anderson_attaches_only_dates_verified_on_programme_pages() -> None:
    names = [
        "Diagnostic Genetics and Genomics",
        "M.S. in Medical Dosimetry",
        "Radiologic Sciences",
        "Individualized MS Program in Biomedical Sciences",
        "Genetic Counseling",
        "Medical Physics",
    ]
    catalogue = "".join(
        f'<a href="https://example.edu/{index}"><h4>{name}</h4></a>'
        for index, name in enumerate(names)
    )
    pages = {
        MD_CATALOG_URL: catalogue,
        DIAGNOSTIC_URL: (
            "Fall 2026 Admission Sept. 15, 2025 Applications open "
            "April 30, 2026 Priority applications deadline; "
            "May 30, 2026 Applications close"
        ),
        DOSIMETRY_URL: (
            "Fall 2027 Admission Process Accepting applications Dec. 1, 2026 "
            "Application deadline March 15, 2027"
        ),
        RADIOLOGIC_URL: (
            "Spring 2027 Admission Process Accepting applications May 1-Sept. 30, 2026"
        ),
    }

    programmes = (
        MDAndersonAdapter().parse_catalog_from_fetcher(pages.__getitem__).programmes
    )

    diagnostic = next(
        row for row in programmes if row.name == "Diagnostic Genetics and Genomics"
    )
    dosimetry = next(
        row for row in programmes if row.name == "M.S. in Medical Dosimetry"
    )
    radiologic = next(row for row in programmes if row.name == "Radiologic Sciences")
    genetic_counseling = next(
        row for row in programmes if row.name == "Genetic Counseling"
    )
    assert len(diagnostic.windows) == 2
    assert dosimetry.windows[0].opens_at == "2026-12-01"
    assert radiologic.windows[0].closes_at == "2026-09-30"
    assert genetic_counseling.windows == []


def test_lausanne_deduplicates_cross_faculty_programmes_and_keeps_close_guidance() -> (
    None
):
    html = """
      <div class="accordion-question">
        <span class="accordion-btn-text">Faculté des lettres</span>
        <div class="accordion-text">
          <a href="/unil/fr/home/menuinst/etudier/masters/humanites-numeriques.html">
            Humanités numériques
          </a>
        </div>
      </div>
      <div class="accordion-question">
        <span class="accordion-btn-text">Programmes interfacultaires</span>
        <div class="accordion-text">
          <a href="/unil/fr/home/menuinst/etudier/masters/humanites-numeriques.html">
            Humanités numériques
          </a>
          <a href="/unil/fr/home/menuinst/etudier/masters/droit-et-economie.html">
            Droit et économie
          </a>
        </div>
      </div>
    """
    application = """
      <h2>Semestre de printemps 2027</h2>
      <table><tr><td>Master</td><td>
        30 novembre 2026 <small>30 septembre si visa en vue d'études</small>
      </td></tr></table>
    """

    programmes = (
        LausanneAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(
            lambda url: application if url == LAUSANNE_APPLICATION_URL else html
        )
        .programmes
    )

    assert [row.name for row in programmes] == [
        "Droit et économie",
        "Humanités numériques",
        "Master admissions",
    ]
    assert [window.closes_at for window in programmes[-1].windows] == [
        "2026-11-30",
        "2026-09-30",
    ]
    assert all(window.opens_at is None for window in programmes[-1].windows)
