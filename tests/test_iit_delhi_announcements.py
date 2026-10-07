import pytest

from gradwindow.programme_adapters.iit_delhi import IITDelhiAdapter

ANNOUNCEMENTS = """
<h1>ADMISSIONS</h1>
<ul><li>The admission portal for foreign nationals seeking admission to the
Ph.D./M.S.(R) Programmes for the 2nd Semester of the Academic Year 2026–27
is now open. The last date for submission of applications is 29.10.2026.
<a href="https://ecampus.iitd.ac.in/IPGADM/login">Apply now</a></li>
<li>The admission portal for national candidates seeking admission to the
Ph.D./M.S.(R) Programmes for the 2nd Semester of the Academic Year 2026–27
will open on 09.10.2026 at 12:00 noon.</li>
<li>Information Brochure: will be uploaded shortly.</li></ul>
"""


def test_second_semester_notices_do_not_combine_applicant_dates():
    assert IITDelhiAdapter.catalogue_granularity == "admissions-route-level"
    catalog = IITDelhiAdapter().parse_catalog(ANNOUNCEMENTS)
    assert catalog.application_opens_at is None
    assert len(catalog.programmes) == 1
    row = catalog.programmes[0]
    assert row.id == "iit-delhi-postgraduate-programmes"
    assert row.windows == []
    assert row.parse_status == "no-deadline"
    assert "foreign nationals" in row.deadline_text
    assert "national candidates" in row.deadline_text
    assert "29.10.2026" in row.deadline_text
    assert "09.10.2026" in row.deadline_text
    assert "not a programme catalogue" in row.deadline_text
    assert "certificate" not in row.deadline_text


def test_new_cycle_does_not_depend_on_hard_coded_year():
    row = (
        IITDelhiAdapter()
        .parse_catalog(ANNOUNCEMENTS.replace("2026", "2027").replace("–27", "–28"))
        .programmes[0]
    )
    assert "2027–28" in row.deadline_text
    assert not row.windows


@pytest.mark.parametrize(
    "html",
    [
        ANNOUNCEMENTS.replace("ecampus.iitd.ac.in", "ecampus.iitd.ac.in.example.com"),
        ANNOUNCEMENTS.replace("2026–27", "unknown"),
        "<!--" + ANNOUNCEMENTS + "-->",
        "<header>" + ANNOUNCEMENTS + "</header>",
        '<h1>ADMISSIONS</h1><a href="https://ecampus.iitd.ac.in/PGADM/">PG Programmes admission</a>',
    ],
)
def test_navigation_or_stale_comment_is_not_an_admissions_notice(html):
    with pytest.raises(ValueError, match="route changed"):
        IITDelhiAdapter().parse_catalog(html)
