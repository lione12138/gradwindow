import json

from gradwindow.programme_adapters.ntu import (
    APPLICATION_URL,
    NTUAdapter,
    catalog_page_url,
)


def test_ntu_matches_official_chinese_intake_names_to_catalogue_programmes() -> None:
    items = [
        {
            "title": (
                "Master of Public Administration (Executive MPA Programme)"
                "(March intake 三月开学)"
            ),
            "url": "/education/graduate-programme/ncpa-mpa-chinese",
            "tag": "Nanyang Centre for Public Administration",
        },
        {
            "title": (
                "Master of Science in Managerial Economics "
                "(Executive MME Programme)(March Intake三月开学)"
            ),
            "url": "/education/graduate-programme/ncpa-mme-chinese",
            "tag": "Nanyang Centre for Public Administration",
        },
    ]
    catalogue = json.dumps({"totalPages": 1, "totalItems": len(items), "items": items})
    application_table = """
    <table>
      <tr><th>Period</th><th>Admission</th><th>Programme</th><th>Open</th><th>Close</th></tr>
      <tr><td>AY2026 / Main</td><td>01-Mar-27</td>
        <td>248 - MASTER OF PUBLIC ADMINISTRATION - CHINESE</td>
        <td>03-Aug-26</td><td>30-Sep-26</td></tr>
      <tr><td>AY2026 / Main</td><td>01-Mar-27</td>
        <td>247 - MSC (MANAGERIAL ECONOMICS) - CHINESE</td>
        <td>03-Aug-26</td><td>30-Sep-26</td></tr>
    </table>
    """
    pages = {
        catalog_page_url(1): catalogue,
        APPLICATION_URL: application_table,
    }

    catalog = NTUAdapter(minimum_expected_programmes=2).parse_catalog_from_fetcher(
        pages.__getitem__
    )

    assert len(catalog.programmes) == 2
    assert all(programme.parse_status == "parsed" for programme in catalog.programmes)
    assert all(len(programme.windows) == 1 for programme in catalog.programmes)
    assert {
        (window.opens_at, window.closes_at, window.intake)
        for programme in catalog.programmes
        for window in programme.windows
    } == {("2026-08-03", "2026-09-30", "March 2027")}


def test_ntu_keeps_matched_windows_and_reports_unmatched_application_rows() -> None:
    items = [
        {
            "title": "Master of Science in Data Science",
            "url": "/education/graduate-programme/msc-data-science",
            "tag": "College of Computing and Data Science",
        }
    ]
    catalogue = json.dumps({"totalPages": 1, "totalItems": 1, "items": items})
    application_table = """
    <table>
      <tr><th>Period</th><th>Admission</th><th>Programme</th><th>Open</th><th>Close</th></tr>
      <tr><td>AY2026 / Semester 2</td><td>11-Jan-27</td>
        <td>277 - MSC(DATA SCIENCE)</td><td>1-Jul-26</td><td>31-Aug-26</td></tr>
      <tr><td>AY2026 / Semester 2</td><td>11-Jan-27</td>
        <td>999 - MSC(NEW OFFICIAL PROGRAMME)</td><td>1-Jul-26</td><td>31-Aug-26</td></tr>
    </table>
    """
    pages = {
        catalog_page_url(1): catalogue,
        APPLICATION_URL: application_table,
    }

    catalog = NTUAdapter(minimum_expected_programmes=1).parse_catalog_from_fetcher(
        pages.__getitem__
    )

    assert catalog.programmes[0].parse_status == "parsed"
    assert len(catalog.programmes[0].windows) == 1
    assert catalog.warnings == [
        {
            "reason": "PROGRAMME_ID_MISMATCH",
            "message": (
                "NTU's official application table contains 1 row that could not "
                "be matched to the official coursework catalogue."
            ),
            "sourceUrl": APPLICATION_URL,
            "programmeKeys": ["new official"],
        }
    ]


def test_ntu_programme_ids_treat_ampersand_as_and() -> None:
    items = [
        {
            "title": "Master of Science in Integrated Circuits & Microelectronics",
            "url": "/education/graduate-programme/msc-integrated-circuits",
            "tag": "School of Electrical and Electronic Engineering",
        },
        {
            "title": "Master of Science in Asset & Wealth Management",
            "url": "/education/graduate-programme/msc-asset-wealth-management",
            "tag": "Nanyang Business School",
        },
    ]
    catalogue = json.dumps({"totalPages": 1, "totalItems": 2, "items": items})
    pages = {
        catalog_page_url(1): catalogue,
        APPLICATION_URL: "<table></table>",
    }

    catalog = NTUAdapter(minimum_expected_programmes=2).parse_catalog_from_fetcher(
        pages.__getitem__
    )

    assert {programme.id for programme in catalog.programmes} == {
        "ntu-asset-wealth-management-msc",
        "ntu-integrated-circuits-and-microelectronics-msc",
    }
