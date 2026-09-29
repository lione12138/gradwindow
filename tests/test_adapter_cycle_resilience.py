import pytest
from test_princeton_programme_adapter import CATALOG_MARKDOWN, DEADLINES_HTML

from gradwindow.programme_adapters import dartmouth, princeton


def test_dartmouth_current_application_page_preserves_catalogue():
    pages = {
        dartmouth.CATALOG_URL: "<h2>Master's Programs (MS and MA)</h2>"
        '<div><a href="/computer">Computer Science</a></div>',
        dartmouth.APPLICATION_URL: "<main><h1>Applying to Dartmouth</h1>"
        "Start Your Application. Application requirements vary by program.</main>",
    }
    catalog = dartmouth.DartmouthAdapter(1).parse_catalog_from_fetcher(
        pages.__getitem__
    )
    assert len(catalog.programmes) == 1
    assert catalog.programmes[0].windows == []
    assert catalog.programmes[0].source_url == "https://graduate.dartmouth.edu/computer"


def test_dartmouth_rejects_unrelated_response():
    pages = {
        dartmouth.CATALOG_URL: "<h2>Master's Programs (MS and MA)</h2>"
        '<div><a href="/computer">Computer Science</a></div>',
        dartmouth.APPLICATION_URL: "<h1>Access denied</h1>",
    }
    with pytest.raises(ValueError):
        dartmouth.DartmouthAdapter(1).parse_catalog_from_fetcher(pages.__getitem__)


@pytest.mark.parametrize("notice", ["is now open", "will open in September 2026"])
def test_princeton_retains_deadlines_without_inventing_opening(notice):
    policy = DEADLINES_HTML.replace("will open on September 15, 2026", notice)
    pages = {princeton.CATALOG_URL: CATALOG_MARKDOWN, princeton.DEADLINES_URL: policy}
    catalog = princeton.PrincetonAdapter(5).parse_catalog_from_fetcher(
        pages.__getitem__
    )
    assert len(catalog.programmes) == 5
    for programme in catalog.programmes:
        assert programme.parse_status == "incomplete"
        assert programme.windows[0].opens_at is None
        assert programme.windows[0].opens_at_basis == "missing"
        assert programme.windows[0].closes_at.startswith("2026-")


def test_princeton_paused_degree_has_no_window():
    catalogue = CATALOG_MARKDOWN + (
        "\n| [Computer Science](https://gradschool.princeton.edu/academics/"
        "degrees-requirements/fields-study/computer-science) | Ph.D. , M.S.E. |\n"
    )
    policy = DEADLINES_HTML.replace(
        "will open on September 15, 2026", "is now open"
    ).replace(
        "<table>",
        "<p>The following degree programs are not accepting applications for "
        "Fall 2027: Population Studies, Computer Science, M.S.E.</p><table>",
    )
    pages = {princeton.CATALOG_URL: catalogue, princeton.DEADLINES_URL: policy}
    catalog = princeton.PrincetonAdapter(6).parse_catalog_from_fetcher(
        pages.__getitem__
    )
    programme = next(
        p for p in catalog.programmes if p.department == "Computer Science"
    )
    assert programme.windows == []
    assert programme.admission_status == "paused"
    assert "Fall 2027" in programme.deadline_text


def test_princeton_pause_is_scoped_to_cycle_and_degree():
    notice = (
        "The following degree programs are not accepting applications for "
        "Fall 2027: Population Studies, Computer Science, M.S.E. Deadline"
    )
    assert princeton._degree_paused(notice, "Computer Science", "M.S.E.", 2027)
    assert not princeton._degree_paused(notice, "Computer Science", "M.Eng.", 2027)
    assert not princeton._degree_paused(notice, "Computer Science", "M.S.E.", 2028)


def test_princeton_missing_cycle_still_fails_closed():
    with pytest.raises(ValueError, match="cycle was not found"):
        princeton._next_cycle_opening_policy("<main>Access denied</main>")
