import pytest

from gradwindow.programme_adapters.nottingham import NottinghamAdapter


def test_course_cards_supply_awards_when_urls_do_not():
    html = """
    <div class="courseDescription"><h3>Cyber Security MSc</h3>
    <a href="/pgstudy/course/taught/cybersecurity"></a></div>
    <div class="courseDescription"><h3>Medical Education MMedSci/PGDip/PGCert</h3>
    <a href="/pgstudy/course/taught/medical-education-mmedsci"></a></div>
    <div class="courseDescription"><h3>Primary PGCE</h3>
    <a href="/pgstudy/course/taught/primary-pgce"></a></div>
    <div class="courseDescription"><h3>Cyber Security PhD</h3>
    <a href="/pgstudy/course/research/cybersecurity"></a></div>
    """
    adapter = NottinghamAdapter(minimum_expected_programmes=2)
    programmes = adapter.parse_pages([html, html]).programmes
    assert [p.name for p in programmes] == [
        "Cyber Security MSc",
        "Medical Education MMedSci/PGDip/PGCert",
    ]
    assert [p.degree_type for p in programmes] == ["MSC", "MMEDSCI"]
    assert all(not p.windows for p in programmes)


PAGE = """
<a href="/pgstudy/course/taught/accounting-and-finance-msc"><span>Accounting and Finance MSc</span></a>
<a href="/pgstudy/course/taught/applied-linguistics-ma"><span>Applied Linguistics MA</span></a>
<a href="/pgstudy/course/research/american-studies-phd"><span>American Studies PhD</span></a>
"""


@pytest.mark.parametrize("award", ["MArch", "MPA", "MSc"])
def test_award_in_card_keeps_url_slug_and_official_host(award):
    card = (
        f'<div class="courseDescription"><h3>Example {award}</h3>'
        '<a href="/pgstudy/course/taught/example"></a></div>'
    )
    external = card.replace("/pgstudy/", "https://example.com/pgstudy/")
    programme = (
        NottinghamAdapter(minimum_expected_programmes=1)
        .parse_pages([card, external])
        .programmes[0]
    )
    assert programme.id == "nottingham-example"
    assert programme.degree_type == award.upper()
    assert (
        programme.source_url
        == "https://www.nottingham.ac.uk/pgstudy/course/taught/example"
    )


def test_nottingham_adapter_keeps_taught_masters_and_deduplicates_pages() -> None:
    catalog = NottinghamAdapter(minimum_expected_programmes=2).parse_pages([PAGE, PAGE])

    assert [item.name for item in catalog.programmes] == [
        "Accounting and Finance MSc",
        "Applied Linguistics MA",
    ]
    assert all("/taught/" in item.source_url for item in catalog.programmes)


def test_nottingham_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        NottinghamAdapter(minimum_expected_programmes=3).parse_pages([PAGE])
