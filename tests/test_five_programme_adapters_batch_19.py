from __future__ import annotations

import json

from gradwindow.programme_adapters.indiana_bloomington import (
    APPLICATION_URL as INDIANA_APPLICATION_URL,
)
from gradwindow.programme_adapters.indiana_bloomington import (
    CATALOG_URL as INDIANA_CATALOG_URL,
)
from gradwindow.programme_adapters.indiana_bloomington import IndianaBloomingtonAdapter
from gradwindow.programme_adapters.nankai import CATALOG_PAGE_URL as NANKAI_CATALOG_PAGE
from gradwindow.programme_adapters.nankai import GUIDE_URL as NANKAI_GUIDE_URL
from gradwindow.programme_adapters.nankai import NankaiAdapter
from gradwindow.programme_adapters.shandong import GUIDE_URL as SHANDONG_GUIDE_URL
from gradwindow.programme_adapters.shandong import ShandongAdapter
from gradwindow.programme_adapters.technion import CATALOG_URL as TECHNION_CATALOG_URL
from gradwindow.programme_adapters.technion import (
    DEADLINES_URL as TECHNION_DEADLINES_URL,
)
from gradwindow.programme_adapters.technion import TechnionAdapter
from gradwindow.programme_adapters.uab_barcelona import (
    APPLICATION_URL as UAB_APPLICATION_URL,
)
from gradwindow.programme_adapters.uab_barcelona import CATALOG_URL as UAB_CATALOG_URL
from gradwindow.programme_adapters.uab_barcelona import UABBarcelonaAdapter


def test_nankai_reads_pdf_catalogue_and_shared_exact_window() -> None:
    pages = {
        NANKAI_CATALOG_PAGE: (
            '<script>showVsbpdfIframe("/__local/fixture.pdf", "100%")</script>'
        ),
        NANKAI_GUIDE_URL: (
            "<h1>Nankai University Postgraduate Programs Overview 2026</h1>"
            "<p>Application Date: 20th October, 2025 – 31th May 2026</p>"
        ),
    }
    entries = (
        ("Chern Institute of Mathematics", "Pure Mathematics", "Chinese"),
        ("College of Software", "Software Engineering", "English"),
    )

    catalog = NankaiAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda url: entries,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 3
    assert catalog.programmes[1].name.endswith("(English-medium)")
    window = catalog.programmes[-1].windows[0]
    assert (window.opens_at, window.closes_at) == ("2025-10-20", "2026-05-31")


def test_shandong_keeps_image_only_guide_out_of_deadline_records() -> None:
    guide = (
        "<title>2026 Application Instructions for International Students "
        "(Master Programs) at Shandong University</title>"
        '<div class="v_news_content">'
        + "".join(f'<img src="/{index}.jpg">' for index in range(6))
        + "</div>"
    )
    pages = {SHANDONG_GUIDE_URL: guide}
    entries = (
        (
            "School of Stomatology",
            "Baotuquan Campus, Jinan",
            "Clinical Stomatology",
            "Chinese",
        ),
        ("School of Economics", "Central Campus, Jinan", "Finance", "English"),
    )

    catalog = ShandongAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        catalogue_fetcher=lambda url: entries,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 2
    assert all(programme.windows == [] for programme in catalog.programmes)
    assert all(
        programme.parse_status == "no-deadline" for programme in catalog.programmes
    )


def test_indiana_reads_official_public_degree_api_and_department_policy() -> None:
    payload = {
        "status": 200,
        "pagination": {"total": 2},
        "data": [
            {
                "name": "Accounting",
                "degree": "Master of Business Administration",
                "diploma_badge": "Master's",
                "campus": "IU Bloomington",
                "schools": [{"name": "Kelley School of Business"}],
                "url": "https://academics.iu.edu/degrees/bloomington/master-of-business-administration/accounting.html",
            },
            {
                "name": "Applied Statistics",
                "degree": "Master of Science",
                "diploma_badge": "Master's",
                "campus": "IU Bloomington",
                "schools": [{"name": "College of Arts and Sciences"}],
                "url": "https://academics.iu.edu/degrees/bloomington/master-of-science/applied-statistics.html",
            },
        ],
    }
    pages = {
        INDIANA_CATALOG_URL: json.dumps(payload),
        INDIANA_APPLICATION_URL: (
            "<h1>How to Apply</h1><p>Departments set their own application "
            "deadlines. Visit your prospective program's website.</p>"
        ),
    }

    catalog = IndianaBloomingtonAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 2
    assert catalog.programmes[0].faculty
    assert all(programme.windows == [] for programme in catalog.programmes)


def test_uab_barcelona_parses_official_masters_by_area() -> None:
    catalogue = """
      <main>
        <h2>Engineering and technology</h2>
        <a href="/sites/ContentServer/estudiar/official-master-s-degrees/general-information/data-engineering-1096480962610.html?param1=100">Data Engineering <span>New</span></a>
        <h2>Sciences and environmental science</h2>
        <a href="/sites/ContentServer/estudiar/official-master-s-degrees/general-information/applied-mathematics-1096480962610.html?param1=200">Applied Mathematics</a>
      </main>
    """
    application = """
      <main><h1>Application for admission to a master's degree</h1>
      <a href="/sites/ContentServer/estudiar/official-master-s-degrees/admission/admission-requirements/data-engineering.html">Data Engineering</a>
      <a href="/sites/ContentServer/estudiar/official-master-s-degrees/admission/admission-requirements/applied-mathematics.html">Applied Mathematics</a></main>
    """
    pages = {UAB_CATALOG_URL: catalogue, UAB_APPLICATION_URL: application}

    catalog = UABBarcelonaAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        minimum_expected_application_links=2,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert [programme.name for programme in catalog.programmes] == [
        "Applied Mathematics",
        "Data Engineering",
    ]
    assert all(programme.windows == [] for programme in catalog.programmes)


def test_technion_parses_units_and_current_winter_window() -> None:
    catalogue = """
      <div class="section-content"><h2>Faculties</h2>
        <h3><a href="https://graduate.technion.ac.il/en/aerospace-engineering/">Aerospace Engineering</a></h3>
      </div>
      <div class="section-content"><h2>Interdisciplinary Programs</h2>
        <h3><a href="https://graduate.technion.ac.il/en/systems-engineering/">Systems Engineering</a></h3>
      </div>
    """
    deadlines = """
      <h1>Registration Dates &amp; Instructions</h1>
      <p>Registration for the Winter Semester of 2026-2027 has begun. Due to the
      current situation, the registration period has been extended until 31.05.2026.</p>
      <table><tr><td>Candidates who studied abroad: Registration to a winter semester</td>
      <td>Between 1.3-30.4</td></tr></table>
    """
    pages = {TECHNION_CATALOG_URL: catalogue, TECHNION_DEADLINES_URL: deadlines}

    catalog = TechnionAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert len(catalog.programmes) == 3
    window = catalog.programmes[-1].windows[0]
    assert (window.opens_at, window.closes_at) == ("2026-03-01", "2026-05-31")
    assert window.opens_at_basis == "official"
