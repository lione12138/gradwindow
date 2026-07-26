from gradwindow.programme_adapters.leeds import LeedsAdapter

HTML = """<article class="uol-results-items__item"><h2><a href="https://search.example/redirect?url=https%3A%2F%2Fcourses.leeds.ac.uk%2F202627%2Ff753%2Fadvanced-computer-science-msc">Advanced Computer Science MSc</a></h2></article><article class="uol-results-items__item"><h2><a href="https://search.example/redirect?url=https%3A%2F%2Fcourses.leeds.ac.uk%2Fcertificate">Digital Certificate</a></h2></article>"""


def test_leeds_parses_direct_official_urls_and_master_degrees() -> None:
    catalog = LeedsAdapter(minimum_expected_programmes=1)._catalog([HTML])
    programme = catalog.programmes[0]
    assert programme.id == "leeds-advanced-computer-science-msc"
    assert programme.source_url.startswith("https://courses.leeds.ac.uk/")
