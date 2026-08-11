from __future__ import annotations

import json

from gradwindow.programme_adapters.deakin import DeakinAdapter
from gradwindow.programme_adapters.kaust import KAUSTAdapter
from gradwindow.programme_adapters.shenzhen import ShenzhenAdapter
from gradwindow.programme_adapters.sustech import SUSTechAdapter
from gradwindow.programme_adapters.swinburne import SwinburneAdapter


def test_kaust_reads_programme_articles_only() -> None:
    html = """
      <h3>KAUST Academic Programs by Division</h3>
      <article class="kaust-category"><h3>Computer Science (CS)</h3>
        <a class="category button" href="https://cemse.kaust.edu.sa/cs">Explore</a>
      </article>
    """

    rows = KAUSTAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Computer Science (CS)", "MS")
    ]


def test_sustech_keeps_only_rows_marked_for_masters() -> None:
    html = """
      <table>
        <tr><th>Code</th><th>Program/ Major</th><th>Doctoral Program</th><th>Master's Program</th></tr>
        <tr><td>070100</td><td>Mathematics</td><td>●</td><td></td></tr>
        <tr><td>070200</td><td>Physics</td><td>●</td><td>●</td></tr>
      </table>
    """

    rows = SUSTechAdapter(minimum_expected_programmes=1).parse_catalog(html).programmes

    assert [row.name for row in rows] == ["Physics"]


def test_shenzhen_extracts_programme_column_from_rowspans() -> None:
    html = """
      <table>
        <tr><td>文科类 Liberal Arts</td><td>国际交流学院 College of International Exchange</td>
          <td>国际中文教育 International Chinese Language Education</td><td>mail@szu.edu.cn</td><td>2</td></tr>
        <tr><td>应用心理 Applied Psychology</td><td>3</td></tr>
      </table>
    """

    rows = ShenzhenAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [row.name for row in rows] == [
        "Applied Psychology",
        "International Chinese Language Education",
    ]


def test_deakin_keeps_current_master_versions_and_deduplicates_names() -> None:
    html = """
      <table></table><table></table>
      <table>
        <tr><td><a href="/new">Master of Data Science</a></td><td>From 2026 onwards</td></tr>
        <tr><td><a href="/old">Master of Data Science</a></td><td>From 2022 onwards</td></tr>
        <tr><td><a href="/closed">Master of Finance</a></td><td>2020 to 2025</td></tr>
      </table>
      <table><tr><td><a href="/research">Master of Arts</a></td><td>From 2020 onwards</td></tr></table>
    """

    rows = DeakinAdapter(minimum_expected_programmes=2).parse_catalog(html).programmes

    assert [row.name for row in rows] == ["Master of Arts", "Master of Data Science"]
    data_science = next(row for row in rows if row.name == "Master of Data Science")
    assert data_science.source_url.endswith("/new")


def test_swinburne_keeps_current_official_master_results_and_base_url() -> None:
    payload = {
        "response": {
            "resultPacket": {
                "results": [
                    {
                        "title": "Master of Data Science",
                        "liveUrl": "https://www.swinburne.edu.au/course/postgraduate/master-data/specialisation/",
                        "listMetadata": {"AccreditationStatus": ["Current"]},
                    },
                    {
                        "title": "Master of Data Science",
                        "liveUrl": "https://www.swinburne.edu.au/course/postgraduate/master-data/",
                        "listMetadata": {"AccreditationStatus": ["Current"]},
                    },
                    {
                        "title": "Master of Old Science",
                        "liveUrl": "https://www.swinburne.edu.au/course/postgraduate/old/",
                        "listMetadata": {"AccreditationStatus": ["Expired"]},
                    },
                ]
            }
        }
    }

    rows = (
        SwinburneAdapter(minimum_expected_programmes=1)
        .parse_catalog(json.dumps(payload))
        .programmes
    )

    assert [row.name for row in rows] == ["Master of Data Science"]
    assert rows[0].source_url.endswith("/master-data/")
