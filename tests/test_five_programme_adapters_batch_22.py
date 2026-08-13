from __future__ import annotations

from gradwindow.programme_adapters.chongqing import ChongqingAdapter
from gradwindow.programme_adapters.goethe_frankfurt import GoetheFrankfurtAdapter
from gradwindow.programme_adapters.padua import PaduaAdapter
from gradwindow.programme_adapters.rutgers_nb import RutgersNBAdapter
from gradwindow.programme_adapters.scut import SCUTAdapter


def test_scut_reads_master_options_and_keeps_two_official_rounds() -> None:
    catalogue = """
      <select id="contentParent_drpZy">
        <option value="">--请选择--</option>
        <option value="020200">020200|应用经济学</option>
        <option value="025100">025100|金融</option>
      </select>
    """
    guide = """
      <p>网上报名时间为2025年10月16日至10月27日
      （网上预报名时间为2025年10月10日至10月13日），每日9:00—22:00。</p>
    """
    adapter = SCUTAdapter(minimum_expected_programmes=2, maximum_expected_programmes=2)

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: catalogue if url == adapter.catalog_url else guide
    ).programmes

    assert {row.name for row in rows if not row.windows} == {"应用经济学", "金融"}
    group = next(row for row in rows if row.windows)
    assert [(window.opens_at, window.closes_at) for window in group.windows] == [
        ("2025-10-10", "2025-10-13"),
        ("2025-10-16", "2025-10-27"),
    ]


def test_chongqing_reads_every_faculty_route_without_inventing_dates() -> None:
    root = """
      <a href="/sszyml/2026/1.html">公共管理学院</a>
      <a href="/sszyml/2026/2.html">经济与工商管理学院</a>
      <p>所有考生均须在教育部规定时间内参加网上报名和网上确认。</p>
    """
    faculty_one = """
      <table><tr><th>专业代码及专业名称</th></tr>
      <tr><td>（全日制）120400 公共管理学 研究方向：01行政管理</td></tr>
      <tr><td>（非全日制）125200 公共管理 【专硕】 研究方向：01行政管理</td></tr>
      </table>
    """
    faculty_two = """
      <table><tr><th>专业代码及专业名称</th></tr>
      <tr><td>（全日制）020200 应用经济学 研究方向：01产业经济学</td></tr>
      </table>
    """

    def fetcher(url: str) -> str:
        if url.endswith("/1.html"):
            return faculty_one
        if url.endswith("/2.html"):
            return faculty_two
        return root

    rows = (
        ChongqingAdapter(
            minimum_expected_programmes=3,
            maximum_expected_programmes=3,
        )
        .parse_catalog_from_fetcher(fetcher)
        .programmes
    )

    assert {row.name for row in rows} == {
        "公共管理学（全日制）",
        "公共管理 【专硕】（非全日制）",
        "应用经济学（全日制）",
    }
    assert all(not row.windows for row in rows)


def test_padua_follows_all_catalogue_pages_and_keeps_course_specific_dates() -> None:
    first = """
      <div>223 results</div>
      <button aria-current="page">1</button><button aria-label="Go to page 2">2</button>
      <a class="CardCorsi-module__cardCorsiBox" href="/en/corsi-di-laurea/data-science">
        <h4>Data Science</h4><span>LM-91 - Data Science</span>
        <span>Master's Degree</span><span>2 years</span>
      </a>
    """
    second = """
      <a class="CardCorsi-module__cardCorsiBox" href="/en/corsi-di-laurea/economics">
        <h4>Economics</h4><span>LM-56 - Economics</span>
        <span>Master's Degree</span><span>2 years</span>
      </a>
    """
    policy = "The degree programmes have different deadlines and entry requirements."
    adapter = PaduaAdapter(minimum_expected_programmes=2)

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: (
            policy
            if url == adapter.application_url
            else second
            if "page=2" in url
            else first
        )
    ).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Data Science", "Master's Degree"),
        ("Economics", "Master's Degree"),
    ]
    assert all(not row.windows for row in rows)


def test_goethe_uses_all_programmes_view_and_requires_route_deadline_policy() -> None:
    catalogue = """
      <article>
        <span aria-description="Course Degree">Master of Science</span>
        <h4>Computer Science</h4>
        <span>Study start semester: Winter semester</span>
        <a href="/en/studium/studiengaenge/computer-science-master">Open</a>
      </article>
      <article>
        <span aria-description="Course Degree">Bachelor of Arts</span>
        <h4>History</h4>
        <span>Study start semester: Winter semester</span>
        <a href="/en/studium/studiengaenge/history-bachelor">Open</a>
      </article>
    """
    policy = "You can find the deadlines for your degree program on the respective degree program pages."
    adapter = GoetheFrankfurtAdapter(minimum_expected_programmes=1)

    rows = adapter.parse_catalog_from_fetcher(
        lambda url: policy if url == adapter.application_url else catalogue
    ).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Computer Science", "Master of Science")
    ]


def test_rutgers_filters_official_search_to_new_brunswick_masters() -> None:
    html = """
      <div>150 Programs(s)</div>
      <p>Then click on Requirements and Deadlines to get the details for your program.</p>
      <table>
        <tr><th>Program</th><th>Area of Study</th><th></th></tr>
        <tr><td>Anthropology (MA) New Brunswick</td><td>Anthropology</td>
          <td><a href="Detail.aspx?id=anthro">Requirements and Deadlines</a></td></tr>
        <tr><td>Data Science (MS) New Brunswick</td><td>Data Science</td>
          <td><a href="Detail.aspx?id=data">Requirements and Deadlines</a></td></tr>
      </table>
    """
    adapter = RutgersNBAdapter(
        minimum_expected_programmes=2,
        maximum_expected_programmes=2,
        search_fetcher=lambda _url: html,
    )

    rows = adapter.parse_catalog_from_fetcher(lambda _url: html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Anthropology", "MA"),
        ("Data Science", "MS"),
    ]
    assert all("Detail.aspx" in row.source_url for row in rows)
