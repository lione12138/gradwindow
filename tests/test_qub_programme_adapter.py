from __future__ import annotations

import pytest

from gradwindow.programme_adapters.qub import (
    CATALOG_URL,
    JANUARY_PROGRAMMES_URL,
    QUBAdapter,
)

CATALOG_HTML = """
<html><body><ul class="course-listing">
  <li><h4><a href="/courses/postgraduate-taught/data-science-artificial-intelligence-ai-msc/">
    Data Science and Artificial Intelligence (AI) <span>MSc</span>
  </a></h4><ul><li><span>Entry year:</span> 2026/27</li>
  <li><span>Level:</span> Postgraduate Taught</li>
  <li><span>Length:</span> 1 year (Full-time)</li></ul></li>
  <li><h4><a href="/courses/postgraduate-taught/law-llm/">
    Law <span>LLM</span>
  </a></h4><ul><li><span>Entry year:</span> 2026/27</li></ul></li>
  <li><h4><a href="/courses/postgraduate-taught/master-business-administration-internship-mba/">
    Master of Business Administration (with Internship) <span>MBA</span>
  </a></h4></li>
  <li><h4><a href="/courses/postgraduate-taught/education-pgcert/">
    Education <span>PgCert</span>
  </a></h4></li>
</ul></body></html>
"""

JANUARY_HTML = """
<html><body>
  <h2>January 2027</h2>
  <table><tbody>
    <tr><td><a href="https://www.qub.ac.uk/courses/postgraduate-taught/law-llm-jan/">LLM Law</a></td><td><a href="https://myportal.qub.ac.uk/">Apply now</a></td></tr>
    <tr><td>MSc Data Science and Artificial Intelligence</td><td><a href="https://myportal.qub.ac.uk/">Apply now</a></td></tr>
    <tr><td>MBA with Internship</td><td><a href="https://myportal.qub.ac.uk/">Apply now</a></td></tr>
  </tbody></table>
</body></html>
"""


def _adapter() -> QUBAdapter:
    return QUBAdapter(minimum_expected_programmes=3, minimum_expected_january=3)


def _fetcher(url: str) -> str:
    return {CATALOG_URL: CATALOG_HTML, JANUARY_PROGRAMMES_URL: JANUARY_HTML}[url]


def test_qub_parses_real_master_cards_and_january_status() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)

    assert [programme.name for programme in catalog.programmes] == [
        "Data Science and Artificial Intelligence (AI)",
        "Law",
        "Master of Business Administration (with Internship)",
    ]
    assert [programme.degree_type for programme in catalog.programmes] == [
        "MSc",
        "LLM",
        "MBA",
    ]
    assert all(
        programme.available_intakes == ["January 2027"]
        for programme in catalog.programmes
    )
    assert all(
        programme.application_status == "open" for programme in catalog.programmes
    )
    assert all(programme.windows == [] for programme in catalog.programmes)
    assert all(
        programme.parse_status == "no-deadline" for programme in catalog.programmes
    )
    assert "no exact opening or closing date" in catalog.programmes[0].deadline_text


def test_qub_filters_postgraduate_certificates() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)

    assert all(programme.degree_type != "PgCert" for programme in catalog.programmes)


def test_qub_rejects_a_truncated_master_catalogue() -> None:
    with pytest.raises(ValueError, match="contained 3 master's programmes"):
        QUBAdapter(
            minimum_expected_programmes=4,
            minimum_expected_january=3,
        ).parse_catalog_from_fetcher(_fetcher)


def test_qub_rejects_a_truncated_january_list() -> None:
    with pytest.raises(ValueError, match="contained 3 January 2027 programmes"):
        QUBAdapter(
            minimum_expected_programmes=3,
            minimum_expected_january=4,
        ).parse_catalog_from_fetcher(_fetcher)


def test_qub_does_not_treat_waf_as_success() -> None:
    def fetcher(url: str) -> str:
        if url == CATALOG_URL:
            return "window.awsWafCookieDomainList = ['www.qub.ac.uk'];"
        return JANUARY_HTML

    with pytest.raises(ValueError, match="access challenge"):
        _adapter().parse_catalog_from_fetcher(fetcher)
