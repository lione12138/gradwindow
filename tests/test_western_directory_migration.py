import pytest

from gradwindow.programme_adapters.western import (
    APPLICATION_URL,
    CATALOG_URL,
    WesternAdapter,
)

DIRECTORY = """<table id="programTable">
<tr class="MASTERS"><td>Computer Science</td><td><a href="program.cfm?p=35">Master of Science</a></td></tr>
<tr class="MASTERS"><td>Music</td><td><a href="program.cfm?p=100">Master of Arts</a></td></tr>
<tr class="MASTERS"><td>Music</td><td><a href="program.cfm?p=101">Master of Music</a></td></tr>
<tr class="DOCTORAL"><td>Music</td><td><a href="program.cfm?p=102">Doctor of Philosophy</a></td></tr>
</table>"""


def test_new_directory_resolves_detail_urls_without_obsolete_programs_folder():
    adapter = WesternAdapter()
    adapter.minimum_expected_programmes = 3
    calls = []

    def fetch(url):
        calls.append(url)
        return DIRECTORY if url == CATALOG_URL else "How to Apply"

    catalog = adapter.parse_catalog_from_fetcher(fetch)
    assert calls == [
        "https://grad.uwo.ca/admissions/explore-our-programs.cfm",
        "https://grad.uwo.ca/admissions/apply-for-admission/index.cfm",
    ]
    assert len(catalog.programmes) == 3
    assert catalog.programmes[0].id == "western-computer-science-msc"
    assert (
        catalog.programmes[0].source_url
        == "https://grad.uwo.ca/admissions/program.cfm?p=35"
    )
    assert all(
        p.application_url == APPLICATION_URL and not p.windows
        for p in catalog.programmes
    )


@pytest.mark.parametrize(
    "row",
    [
        "<td>Music</td>",
        '<td></td><td><a href="program.cfm?p=101">Master of Music</a></td>',
        "<td>Music</td><td>Master of Music</td>",
    ],
)
def test_incomplete_master_row_fails_instead_of_silently_disappearing(row):
    with pytest.raises(ValueError, match="Western master's row"):
        WesternAdapter().extract_entries(
            f'<table id="programTable"><tr class="MASTERS">{row}</tr></table>'
        )


def test_redirected_homepage_does_not_pass_as_directory():
    with pytest.raises(ValueError, match="expected at least 80"):
        WesternAdapter().parse_catalog(
            "<h1>School of Graduate and Postdoctoral Studies</h1>"
        )
