import pytest

from gradwindow.programme_adapters.deakin import CATALOG_URL, DeakinAdapter


def test_missing_catalogue_notes_require_current_matching_detail():
    catalogue = (
        "<table></table><table></table><table>"
        + """
      <tr><td><a href="/course.php?course=H718&version=2">Master of Dietetics</a></td></tr>
      <tr><td><a href="/course.php?course=H718&version=1">Master of Dietetics</a></td><td>For students who commenced from 2006 to 2024</td></tr>
      <tr><td><a href="/course.php?course=M726&version=2">Master of Laws</a></td></tr>
    </table><table></table>"""
    )
    requested = []

    def fetch(url):
        requested.append(url)
        if url == CATALOG_URL:
            return catalogue
        code = "H718" if "H718" in url else "M726"
        note = "2025 onwards" if code == "H718" else "2010 to 2020"
        return f"""<table>
        <tr><th>Deakin course code</th><td>{code}</td></tr>
        <tr><th>Course version</th><td>2</td></tr>
        <tr><th>Course information</th><td>For students who commenced from {note}</td></tr>
        </table>"""

    programmes = (
        DeakinAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(fetch)
        .programmes
    )
    assert [p.name for p in programmes] == ["Master of Dietetics"]
    assert all("version=1" not in url for url in requested)
    assert programmes[0].windows == []


@pytest.mark.parametrize(
    "code,version,note",
    [
        ("WRONG", "2", "For students who commenced from 2025 onwards"),
        ("H718", "1", "For students who commenced from 2025 onwards"),
        ("H718", "2", "For students who commenced from 2020 to 2024"),
        ("H718", "2", ""),
    ],
)
def test_does_not_accept_wrong_or_unverified_course_version(code, version, note):
    catalogue = """<table></table><table></table><table>
    <tr><td><a href="/course.php?course=H718&version=2">Master of Dietetics</a></td></tr>
    </table><table></table>"""
    detail = f"""<table>
    <tr><th>Deakin course code</th><td>{code}</td></tr>
    <tr><th>Course version</th><td>{version}</td></tr>
    <tr><th>Course information</th><td>{note}</td></tr></table>"""
    with pytest.raises(ValueError, match="expected at least 1"):
        DeakinAdapter(minimum_expected_programmes=1).parse_catalog_from_fetcher(
            lambda url: catalogue if url == CATALOG_URL else detail
        )
