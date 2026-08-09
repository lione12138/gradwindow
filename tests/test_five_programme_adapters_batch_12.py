from __future__ import annotations

from gradwindow.programme_adapters.hanyang import HanyangAdapter
from gradwindow.programme_adapters.tue import TUEAdapter
from gradwindow.programme_adapters.uc_davis import UCDavisAdapter
from gradwindow.programme_adapters.usc import USCAdapter
from gradwindow.programme_adapters.utm import UTMAdapter


def test_uc_davis_monitors_the_official_graduate_directory() -> None:
    rows = (
        UCDavisAdapter()
        .parse_catalog(
            """<urlset>
        <url><loc>https://grad.ucdavis.edu/graduate-programs</loc></url>
        </urlset>"""
        )
        .programmes
    )
    assert [(row.name, row.parse_status) for row in rows] == [
        ("Graduate programs directory", "no-deadline")
    ]


def test_tue_follows_load_more_fragments() -> None:
    adapter = TUEAdapter(minimum_expected_programmes=2)
    first = """
      <a href="/en/education/graduate-school/master-applied-physics">
        <h3 class="entryBlock-title">Master Applied Physics</h3>
      </a>
      <a class="loadmore" href="/more?offset=12">Load more</a>
    """
    second = """
      <a href="/en/education/graduate-school/master-computer-science-and-engineering">
        <h3 class="entryBlock-title">Master Computer Science and Engineering</h3>
      </a>
    """
    rows = adapter.parse_catalog_from_fetcher(
        lambda url: second if "offset=12" in url else first
    ).programmes
    assert [row.name for row in rows] == [
        "Master Applied Physics",
        "Master Computer Science and Engineering",
    ]


def test_usc_combines_master_filters_and_follows_pagination() -> None:
    adapter = USCAdapter(minimum_expected_programmes=2)
    index = """
      <input id="ms" name="program-degrees[]" value="master-of-science">
      <label for="ms">Master of Science</label>
      <input id="phd" name="program-degrees[]" value="doctor-of-philosophy">
      <label for="phd">Doctor of Philosophy</label>
    """
    first = """
      <li><span class="item-title">Analytics (MS)</span>
        <a href="https://catalogue.usc.edu/preview_program.php?poid=1">Learn More</a>
      </li>
      <nav class="pager"><a href="https://www.usc.edu/graduate-professional/page/2/?program-degrees%5B0%5D=master-of-science">Next page</a></nav>
    """
    second = """
      <li><span class="item-title">Computer Science (MS)</span>
        <a href="https://catalogue.usc.edu/preview_program.php?poid=2">Learn More</a>
      </li>
    """

    def fetcher(url: str) -> str:
        if url == adapter.catalog_url:
            return index
        return second if "/page/2/" in url else first

    rows = adapter.parse_catalog_from_fetcher(fetcher).programmes
    assert [row.name for row in rows] == ["Analytics (MS)", "Computer Science (MS)"]


def test_hanyang_extracts_only_rows_with_a_masters_route() -> None:
    adapter = HanyangAdapter(minimum_expected_programmes=2)
    rows = adapter.parse_catalog(
        """Ⅱ. Fields of Study
        Department of Electrical Engineering○○
        Department of Computer Science○○
        Department of Artificial IntelligenceX○
        School of Architecture - Architectural Design II○X
        Ⅲ. Application Requirements"""
    ).programmes
    assert [row.name for row in rows] == [
        "Department of Computer Science",
        "Department of Electrical Engineering",
        "School of Architecture - Architectural Design II",
    ]
    assert rows[0].id == "hanyang-department-computer-science"


def test_utm_monitors_the_postgraduate_link_on_the_official_homepage() -> None:
    rows = (
        UTMAdapter()
        .parse_catalog(
            '<a href="http://admission.utm.my/malaysian-postgraduate-study/">'
            "Postgraduate Programmes</a>"
        )
        .programmes
    )
    assert rows[0].name == "Postgraduate programmes directory"
    assert rows[0].parse_status == "no-deadline"
