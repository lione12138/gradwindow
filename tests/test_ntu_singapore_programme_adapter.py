import json

import pytest

from gradwindow.programme_adapters.base import ParserZeroResultError
from gradwindow.programme_adapters.ntu import (
    APPLICATION_URL,
    WINDOW_URL,
    NTUAdapter,
    _application_windows_from_api,
    catalog_page_url,
)


def _window_api_payload() -> str:
    return json.dumps(
        {
            "versionInfo": {
                "hasModuleVersionChanged": False,
                "hasApiVersionChanged": False,
            },
            "data": {
                "List": {
                    "List": [
                        {
                            "Year": "2026",
                            "Sem": "2",
                            "Term": "S",
                            "AdmissionDate": "11-01-2027",
                            "AdmControlList": {
                                "List": [
                                    {
                                        "OpenDate": "2026-07-01",
                                        "CloseDate": "2026-08-31",
                                        "CourseCode": "277",
                                        "ProgramName": "MSC(DATA SCIENCE)",
                                    }
                                ]
                            },
                        }
                    ]
                }
            },
        }
    )


def test_ntu_parses_outsystems_application_service_payload() -> None:
    windows, evidence = _application_windows_from_api(_window_api_payload())

    assert list(windows) == ["data science"]
    window = windows["data science"][0]
    assert window.round == "Semester 2"
    assert window.intake == "January 2027"
    assert window.opens_at == "2026-07-01"
    assert window.closes_at == "2026-08-31"
    assert window.applicant_categories == ["all"]
    assert window.source_url == APPLICATION_URL
    assert "official live application service" in evidence["data science"]


def test_ntu_prefers_outsystems_application_service_over_html_shell() -> None:
    items = [
        {
            "title": "Master of Science in Data Science",
            "url": "/education/graduate-programme/msc-data-science",
            "tag": "College of Computing and Data Science",
        }
    ]
    catalogue = json.dumps({"totalPages": 1, "totalItems": 1, "items": items})

    def fetcher(url: str) -> str:
        if url == catalog_page_url(1):
            return catalogue
        raise AssertionError(f"HTML fallback used for {url}")

    catalog = NTUAdapter(
        minimum_expected_programmes=1,
        window_api_fetcher=_window_api_payload,
    ).parse_catalog_from_fetcher(fetcher)

    programme = catalog.programmes[0]
    assert programme.parse_status == "parsed"
    assert programme.retrieval_method == "official-outsystems-api"
    assert len(programme.windows) == 1


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
        WINDOW_URL: application_table,
    }

    catalog = NTUAdapter(
        minimum_expected_programmes=2,
        window_api_fetcher=None,
    ).parse_catalog_from_fetcher(pages.__getitem__)

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
        WINDOW_URL: application_table,
    }

    catalog = NTUAdapter(
        minimum_expected_programmes=1,
        window_api_fetcher=None,
    ).parse_catalog_from_fetcher(pages.__getitem__)

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
        WINDOW_URL: "<p>No programs for entered Year, Sem and Term Type</p>",
    }

    catalog = NTUAdapter(
        minimum_expected_programmes=2,
        window_api_fetcher=None,
    ).parse_catalog_from_fetcher(pages.__getitem__)

    assert {programme.id for programme in catalog.programmes} == {
        "ntu-asset-wealth-management-msc",
        "ntu-integrated-circuits-and-microelectronics-msc",
    }


def test_ntu_uses_browser_rendering_when_live_table_parse_returns_zero() -> None:
    items = [
        {
            "title": "Master of Science in Data Science",
            "url": "/education/graduate-programme/msc-data-science",
            "tag": "College of Computing and Data Science",
        }
    ]
    catalogue = json.dumps({"totalPages": 1, "totalItems": 1, "items": items})
    direct_shell = """
    <h2>The following programme(s) are open for application</h2>
    <div>Opening Date</div><div>Closing Date</div>
    """
    rendered_table = """
    <h2>The following programme(s) are open for application:</h2>
    <div class="table-grid">
      <div class="mainContainer">AY2026 / Semester 2</div>
      <div class="mainContainer">Admission Date: 11-Jan-2027</div>
      <div>Programme Name</div><div>Application Period</div>
      <div class="table-cell">
        <div class="innerList">277 - MSC(DATA SCIENCE)</div>
        <div class="innerList">01-Jul-2026 - 31-Aug-2026</div>
      </div>
    </div>
    """
    pages = {catalog_page_url(1): catalogue, WINDOW_URL: direct_shell}

    catalog = NTUAdapter(
        minimum_expected_programmes=1,
        window_api_fetcher=None,
        browser_content_fetcher=lambda url: (
            rendered_table
            if url == WINDOW_URL
            else (_ for _ in ()).throw(AssertionError(url))
        ),
    ).parse_catalog_from_fetcher(pages.__getitem__)

    programme = catalog.programmes[0]
    assert programme.parse_status == "parsed"
    assert programme.retrieval_method == "cloudflare-browser-rendering"
    assert len(programme.windows) == 1


def test_ntu_rejects_zero_windows_when_official_page_contains_date_signals() -> None:
    items = [
        {
            "title": "Master of Science in Data Science",
            "url": "/education/graduate-programme/msc-data-science",
            "tag": "College of Computing and Data Science",
        }
    ]
    catalogue = json.dumps({"totalPages": 1, "totalItems": 1, "items": items})
    malformed_table = """
    <h2>The following programme(s) are open for application</h2>
    <table>
      <tr><th>Programme</th><th>Opening Date</th><th>Closing Date</th></tr>
      <tr><td>MSC(DATA SCIENCE)</td><td>1-Jul-26</td><td>31-Aug-26</td></tr>
    </table>
    """
    pages = {catalog_page_url(1): catalogue, WINDOW_URL: malformed_table}

    with pytest.raises(ParserZeroResultError, match="date signals.*zero windows"):
        NTUAdapter(
            minimum_expected_programmes=1,
            window_api_fetcher=None,
            browser_content_fetcher=lambda _url: malformed_table,
        ).parse_catalog_from_fetcher(pages.__getitem__)
