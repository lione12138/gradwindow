from __future__ import annotations

import json

from gradwindow.programme_adapters.antwerp import (
    APPLICATION_URL as ANTWERP_APPLICATION_URL,
)
from gradwindow.programme_adapters.antwerp import CATALOG_URL as ANTWERP_CATALOG_URL
from gradwindow.programme_adapters.antwerp import AntwerpAdapter
from gradwindow.programme_adapters.freiburg import (
    APPLICATION_URL as FREIBURG_APPLICATION_URL,
)
from gradwindow.programme_adapters.freiburg import CATALOG_URL as FREIBURG_CATALOG_URL
from gradwindow.programme_adapters.freiburg import FreiburgAdapter
from gradwindow.programme_adapters.notre_dame import (
    APPLICATION_URL as NOTRE_DAME_APPLICATION_URL,
)
from gradwindow.programme_adapters.notre_dame import (
    CATALOG_URL as NOTRE_DAME_CATALOG_URL,
)
from gradwindow.programme_adapters.notre_dame import NotreDameAdapter
from gradwindow.programme_adapters.ottawa import (
    APPLICATION_URL as OTTAWA_APPLICATION_URL,
)
from gradwindow.programme_adapters.ottawa import CATALOG_URL as OTTAWA_CATALOG_URL
from gradwindow.programme_adapters.ottawa import OttawaAdapter
from gradwindow.programme_adapters.wurzburg import WurzburgAdapter


def test_antwerp_reads_official_english_master_cards() -> None:
    pages = {
        ANTWERP_CATALOG_URL: """
          <main id="main">
            <a class="wrap" href="/en/study/programmes/data-science/">
              <h3 class="heading">Data Science</h3>
              <div class="spec levels"><div class="value">Master</div></div>
            </a>
            <a class="wrap" href="/en/study/programmes/bachelor/">
              <h3 class="heading">History</h3>
              <div class="spec levels"><div class="value">Bachelor</div></div>
            </a>
          </main>
        """,
        ANTWERP_APPLICATION_URL: "How to apply for a Master programme.",
    }

    rows = (
        AntwerpAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [("Data Science", "Master")]


def test_ottawa_reads_master_and_maitrise_catalogue_links() -> None:
    pages = {
        OTTAWA_CATALOG_URL: """
          <main><ul>
            <li><a href="/en/graduate/master-computer-science/">Master of Computer Science</a></li>
            <li><a href="/en/graduate/maitrise-droit/">Maîtrise en droit</a></li>
            <li><a href="/en/graduate/doctorate-history/">Doctorate History</a></li>
          </ul></main>
        """,
        OTTAWA_APPLICATION_URL: "Check your deadlines and requirements before applying through OUAC.",
    }

    rows = (
        OttawaAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Master of Computer Science", "Master"),
        ("Maîtrise en droit", "Maîtrise"),
    ]


def test_notre_dame_keeps_only_graduate_master_cards() -> None:
    pages = {
        NOTRE_DAME_CATALOG_URL: """
          <div class="card"><h2 class="card-title"><a href="/ms/">Data Science: M.S.</a></h2>
            <p class="card-meta">Graduate - College of Science</p></div>
          <div class="card"><h2 class="card-title"><a href="/phd/">History: Ph.D.</a></h2>
            <p class="card-meta">Graduate - College of Arts and Letters</p></div>
          <div class="card"><h2 class="card-title"><a href="/ba/">History</a></h2>
            <p class="card-meta">Undergraduate - College of Arts and Letters</p></div>
        """,
        NOTRE_DAME_APPLICATION_URL: (
            "Requirements for admission to graduate programs vary by program."
        ),
    }

    rows = (
        NotreDameAdapter(minimum_expected_programmes=1)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Data Science: M.S.", "Master")
    ]


def test_freiburg_reads_active_masters_from_first_party_api() -> None:
    pages = {
        FREIBURG_CATALOG_URL: json.dumps(
            {
                "data": [
                    {
                        "id": 181,
                        "nameen": "Computer Science",
                        "namede": "Informatik",
                        "abschlussnameen": "Master of Science (M.Sc.)",
                        "status": 1,
                    },
                    {
                        "id": 740,
                        "nameen": "Computer Science",
                        "abschlussnameen": "Master of Education (M.Ed.)",
                        "fachnameen": "Extension subject (120 ECTS credits)",
                        "status": 1,
                    },
                    {
                        "id": 182,
                        "nameen": "Old Programme",
                        "abschlussnameen": "Master of Arts (M.A.)",
                        "status": -1,
                    },
                ]
            }
        ),
        FREIBURG_APPLICATION_URL: (
            "Applying for Master's programmes uses the online application portal."
        ),
    }

    rows = (
        FreiburgAdapter(minimum_expected_programmes=2)
        .parse_catalog_from_fetcher(pages.__getitem__)
        .programmes
    )

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Computer Science", "Master of Science (M.Sc.)"),
        (
            "Computer Science (Extension subject (120 ECTS credits))",
            "Master of Education (M.Ed.)",
        ),
    ]


def test_wurzburg_reads_central_master_application_table() -> None:
    html = """
      <table><tr><th>Programme</th><th>Apply</th><th>Intake</th><th>Period</th></tr>
        <tr><td>Master's programmes (unless otherwise specified)</td>
          <td></td><td></td><td></td></tr>
        <tr><td><a href="/programme/data-science/">Data Science (120, M.Sc.)</a></td>
          <td>WueStudy</td><td>WS</td><td>End of May until July 15th</td></tr>
        <tr><td><a href="/programme/math-data/">Mathematical Data Science, 120, MSc)</a></td>
          <td>WueStudy</td><td>WS</td><td>End of May until July 15th</td></tr>
        <tr><td><a href="/programme/llm/">LL.M. Law (LL.M. for foreign law graduates)</a></td>
          <td>WueStudy</td><td>WS</td><td>End of May until July 15th</td></tr>
        <tr><td>Additional special education qualification</td>
          <td>WueStudy</td><td>WS</td><td>Application period</td></tr>
      </table>
    """

    rows = WurzburgAdapter(minimum_expected_programmes=3).parse_catalog(html).programmes

    assert [(row.name, row.degree_type) for row in rows] == [
        ("Data Science", "M.Sc."),
        ("LL.M. Law", "LL.M."),
        ("Mathematical Data Science", "MSc"),
    ]
