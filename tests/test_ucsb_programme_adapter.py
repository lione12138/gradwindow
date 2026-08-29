from __future__ import annotations

import pytest

from gradwindow.programme_adapters.ucsb import (
    CATALOG_URL,
    SEARCH_URL,
    UCSBAdapter,
)

CHEMISTRY_DEPT_URL = f"{CATALOG_URL}?cmd=dept&code=CHEM"
COMPUTER_SCIENCE_DEPT_URL = f"{CATALOG_URL}?cmd=dept&code=CMPSC"
CHEMISTRY_EMBEDDED_URL = f"{CATALOG_URL}?cmd=prog&code=CHEM-PHD-CHEM-MS-0"
CHEMISTRY_FIVE_YEAR_URL = f"{CATALOG_URL}?cmd=prog&code=CHEM-MS-1"
COMPUTER_SCIENCE_URL = f"{CATALOG_URL}?cmd=prog&code=CMPSC-MS-0"

ROOT_HTML = """
<html><body>
  <p>Note: Masters/Ph.D. programs require application to, and enrollment in,
  the doctoral program.</p>
  <script>FW.Lazy.Fetch("?cmd=search", $("#results"));</script>
</body></html>
"""
SEARCH_HTML = f"""
<div class="list-group">
  <a href="{CHEMISTRY_DEPT_URL}">Chemistry and Biochemistry</a>
  <a href="{COMPUTER_SCIENCE_DEPT_URL}">Computer Science</a>
</div>
"""
CHEMISTRY_DEPT_HTML = f"""
<html><body><h1>Chemistry and Biochemistry</h1>
  <a href="{CHEMISTRY_EMBEDDED_URL}">Ph.D. / MS - Chemistry</a>
  <a href="{CHEMISTRY_FIVE_YEAR_URL}">MS - Chemistry (Five-Year Program) Current UCSB Undergraduates Only</a>
  <a href="?cmd=prog&amp;code=CHEM-PHD-0">Ph.D. - Chemistry</a>
</body></html>
"""
COMPUTER_SCIENCE_DEPT_HTML = f"""
<html><body><h1>Computer Science</h1>
  <a href="{COMPUTER_SCIENCE_URL}">MS - Computer Science</a>
</body></html>
"""


def _detail(rows: str) -> str:
    return f"""
    <html><body><h2>Application Quarter(s) and Deadline(s)</h2>
      <table><thead><tr>
        <th>Application Quarter</th><th>Priority Financial Deadline</th>
        <th>Priority Deadline</th><th>Final Deadline</th>
      </tr></thead><tbody>{rows}</tbody></table>
    </body></html>
    """


DETAILS = {
    CHEMISTRY_EMBEDDED_URL: _detail(
        "<tr><td>Fall 2027</td><td>N/A</td><td>Tuesday, December 1, 2026</td><td>N/A</td></tr>"
    ),
    CHEMISTRY_FIVE_YEAR_URL: _detail(
        "<tr><td>Fall 2027</td><td>N/A</td><td>N/A</td><td>Wednesday, December 2, 2026</td></tr>"
    ),
    COMPUTER_SCIENCE_URL: _detail(
        "<tr><td>Fall 2027</td><td>Friday, January 15, 2027</td><td>N/A</td><td>Wednesday, December 16, 2026</td></tr>"
    ),
}


def _adapter() -> UCSBAdapter:
    return UCSBAdapter(minimum_expected_departments=2, minimum_expected_programmes=3)


def _fetcher(url: str) -> str:
    documents = {
        CATALOG_URL: ROOT_HTML,
        SEARCH_URL: SEARCH_HTML,
        CHEMISTRY_DEPT_URL: CHEMISTRY_DEPT_HTML,
        COMPUTER_SCIENCE_DEPT_URL: COMPUTER_SCIENCE_DEPT_HTML,
        **DETAILS,
    }
    return documents[url]


def test_ucsb_uses_the_slate_portal_backend_and_classifies_routes() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)
    programmes = {item.id: item for item in catalog.programmes}

    embedded = programmes["ucsb-chemistry-ms"]
    restricted = programmes[
        "ucsb-chemistry-five-year-program-current-ucsb-undergraduates-only-ms"
    ]
    direct = programmes["ucsb-computer-science-ms"]

    assert embedded.admission_route == "master-phd-embedded"
    assert restricted.admission_route == "restricted-master"
    assert direct.admission_route == "direct-master"
    assert embedded.windows[0].closes_at == "2026-12-01"
    assert restricted.windows[0].closes_at == "2026-12-02"
    assert [window.round for window in direct.windows] == [
        "Priority financial deadline",
        "Final deadline",
    ]
    assert all(window.opens_at is None for window in direct.windows)
    assert all(window.intake == "Fall 2027" for window in direct.windows)
    assert all(item.parse_status == "incomplete" for item in catalog.programmes)


def test_ucsb_ignores_phd_only_routes() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)

    assert len(catalog.programmes) == 3
    assert all(programme.degree_type == "MS" for programme in catalog.programmes)


def test_ucsb_requires_the_official_embedded_master_policy() -> None:
    def fetcher(url: str) -> str:
        if url == CATALOG_URL:
            return "<html><body>Department Directory</body></html>"
        return _fetcher(url)

    with pytest.raises(ValueError, match="doctoral-program enrollment policy"):
        _adapter().parse_catalog_from_fetcher(fetcher)


def test_ucsb_rejects_a_truncated_department_registry() -> None:
    with pytest.raises(ValueError, match="contained 2 departments"):
        UCSBAdapter(
            minimum_expected_departments=3,
            minimum_expected_programmes=3,
        ).parse_catalog_from_fetcher(_fetcher)


def test_ucsb_requires_a_deadline_table_for_each_master_route() -> None:
    def fetcher(url: str) -> str:
        if url == COMPUTER_SCIENCE_URL:
            return "<html><body><h1>MS - Computer Science</h1></body></html>"
        return _fetcher(url)

    with pytest.raises(ValueError, match="deadline table"):
        _adapter().parse_catalog_from_fetcher(fetcher)
