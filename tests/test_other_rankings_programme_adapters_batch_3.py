from gradwindow.programme_adapters.bonn import CATALOG_URL as BONN_CATALOG_URL
from gradwindow.programme_adapters.bonn import DEADLINES_URL as BONN_DEADLINES_URL
from gradwindow.programme_adapters.bonn import BonnAdapter
from gradwindow.programme_adapters.colorado_boulder import ColoradoBoulderAdapter
from gradwindow.programme_adapters.ohio_state import OhioStateAdapter
from gradwindow.programme_adapters.sun_yat_sen import CATALOG_URL as SYSU_CATALOG_URL
from gradwindow.programme_adapters.sun_yat_sen import SunYatSenAdapter
from gradwindow.programme_adapters.vanderbilt import (
    ADMISSIONS_URL as VANDERBILT_ADMISSIONS_URL,
)
from gradwindow.programme_adapters.vanderbilt import (
    CATALOG_URL as VANDERBILT_CATALOG_URL,
)
from gradwindow.programme_adapters.vanderbilt import VanderbiltAdapter


def test_colorado_boulder_reads_only_masters_routes() -> None:
    html = """
      <a href="/graduate/colleges-schools/arts-sciences/programs-study/history/ma/">
        History -\u200b Master of Arts (MA)</a>
      <a href="/graduate/colleges-schools/engineering/programs-study/data/ms/">
        Data Science - Master of Science (MS)</a>
      <a href="/graduate/colleges-schools/arts-sciences/programs-study/history/phd/">
        History - Doctor of Philosophy (PhD)</a>
    """
    rows = (
        ColoradoBoulderAdapter(minimum_expected_programmes=2)
        .parse_catalog(html)
        .programmes
    )

    assert [row.name for row in rows] == ["Data Science", "History"]
    assert rows[0].degree_type == "Master of Science (MS)"
    assert all(row.windows == [] for row in rows)


def test_vanderbilt_reads_official_program_finder_api() -> None:
    payload = [
        {
            "program_id": 10,
            "program": "Applied Behavior Analysis &amp; Education",
            "masters": "https://peabody.vanderbilt.edu/aba/",
            "masters_type": "M.Ed.",
            "schoollist": ["Peabody College"],
        },
        {
            "program_id": 11,
            "program": "History",
            "masters": "",
            "schoollist": ["Graduate School"],
        },
    ]
    pages = {
        VANDERBILT_CATALOG_URL: (
            '<div data-url_request="https://web.dev-api.vanderbilt.edu/'
            'program-finder"></div>'
        ),
        VANDERBILT_ADMISSIONS_URL: (
            "Applications open August 1st, deadlines vary by program"
        ),
    }
    rows = (
        VanderbiltAdapter(
            minimum_expected_programmes=1, api_fetcher=lambda _url: payload
        )
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )

    assert [row.name for row in rows] == ["Applied Behavior Analysis & Education"]
    assert rows[0].degree_type == "M.Ed."
    assert rows[0].faculty == "Peabody College"


def test_ohio_state_reads_master_programme_links() -> None:
    html = """
      <a href="program.aspx?prog=0004">Aerospace Engineering - Master of Science</a>
      <a href="program.aspx?prog=0017">Architecture - Master of Architecture</a>
      <a href="program.aspx?prog=0018">Architecture - Doctor of Philosophy</a>
    """
    rows = (
        OhioStateAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes
    )

    assert [row.id for row in rows] == ["ohio-state-0004", "ohio-state-0017"]
    assert rows[1].degree_type == "Master of Architecture"


def test_sun_yat_sen_keeps_faculty_and_subject_code_from_pdf() -> None:
    article = """
      <a href="/zsw/files/rules.pdf">招生简章</a>
      <a href="/zsw/files/catalog.pdf">中山大学2026年硕士研究生招生学科专业目录</a>
    """
    pdf_text = """
      100 岭南学院 155
      020100 理论经济学 10 ①101 思想政治理论
      020200 应用经济学 25
      104 岭南学院（深圳经济研究院） 140
      0251Z1 金融科技 80 ②204 英语（二）
    """
    rows = (
        SunYatSenAdapter(
            minimum_expected_programmes=3,
            pdf_text_fetcher=lambda _url: pdf_text,
        )
        .parse_catalog_from_fetcher(
            lambda url: article if url == SYSU_CATALOG_URL else ""
        )
        .programmes
    )

    assert [row.name for row in rows] == ["理论经济学", "应用经济学", "金融科技"]
    assert rows[-1].faculty == "岭南学院（深圳经济研究院）"
    assert rows[-1].id == "sysu-104-0251z1"


def test_bonn_follows_official_catalogue_pagination() -> None:
    first = """
      <label class="results-count">Results 31</label>
      <a class="course" href="/en/studying/programs/agriculture">
        <span class="graduation-title">Master of Science, Single-Subject</span>
        <label class="title">Agriculture</label>
      </a>
    """
    second = """
      <a class="course" href="/en/studying/programs/history">
        <span class="graduation-title">Master of Arts, Single-Subject</span>
        <label class="title">History</label>
      </a>
    """
    pages = {
        BONN_CATALOG_URL: first,
        f"{BONN_CATALOG_URL}?b_start%3Aint=30": second,
        BONN_DEADLINES_URL: (
            "There are no uniform rules governing application deadlines for "
            "postgraduate degree programs."
        ),
    }
    rows = (
        BonnAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(lambda url: pages[url])
        .programmes
    )

    assert [row.name for row in rows] == ["Agriculture", "History"]
    assert all(row.windows == [] for row in rows)
