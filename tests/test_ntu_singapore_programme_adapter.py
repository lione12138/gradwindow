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
