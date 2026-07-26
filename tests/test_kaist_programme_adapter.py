from gradwindow.programme_adapters.kaist import CATALOG_URL, TIMELINE_URL, KAISTAdapter

CATALOGUE = """<h4>College of Engineering</h4><li><h5 class="h-accordion-tit"><span>Computer Science</span><a href="https://cs.kaist.ac.kr/"></a></h5><div>Offered Degrees Master's Ph.D.</div></li>"""
TIMELINE = "<p>Spring 2027 Entry: August 18 – September 1, 2026</p>"


def test_kaist_parses_programmes_and_exact_spring_window() -> None:
    catalog = KAISTAdapter(minimum_expected_programmes=1).parse_catalog_from_fetcher(
        lambda url: {CATALOG_URL: CATALOGUE, TIMELINE_URL: TIMELINE}[url]
    )
    programme = catalog.programmes[0]
    assert programme.id == "kaist-computer-science-master"
    assert (programme.windows[0].opens_at, programme.windows[0].closes_at) == (
        "2026-08-18",
        "2026-09-01",
    )
