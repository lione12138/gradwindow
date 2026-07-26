from gradwindow.programme_adapters.um import CATALOG_URL, DEADLINES_URL, UMAdapter

ROOT = '<a href="pg-faculty-of-computer-science-and-it">COMPUTER SCIENCE</a>'
FACULTY = '<div class="course-card coursework"><a href="master-of-computer-science-applied-computing-coursework">Master of Computer Science (Applied Computing)</a></div><div class="course-card research"><a href="master-of-computer-science-research">Master of Computer Science</a></div>'
DATES = """<table><tr><td>POSTGRADUATE - FOR MALAYSIAN AND INTERNATIONAL Semester I (October) Intake Academic Session 2026/2027 09 Feb 2026 30 Aug 2026 Mode of Programme: * Coursework * Mixed Mode</td></tr><tr><td>POSTGRADUATE - FOR MALAYSIAN AND INTERNATIONAL 27 Apr 2026 22 Nov 2026 Mode of Programme: * Research</td></tr></table>"""


def test_um_fetches_faculties_and_applies_mode_policies() -> None:
    pages = {
        CATALOG_URL: ROOT,
        DEADLINES_URL: DATES,
        "https://study.um.edu.my/pg-faculty-of-computer-science-and-it": FACULTY,
    }
    catalog = UMAdapter(minimum_expected_programmes=2).parse_catalog_from_fetcher(
        lambda url: pages[url]
    )
    assert catalog.programmes[0].windows[0].opens_at in {"2026-02-09", "2026-04-27"}
    by_id = {item.id: item for item in catalog.programmes}
    assert (
        by_id["um-computer-science-applied-computing-master"].windows[0].closes_at
        == "2026-08-30"
    )
