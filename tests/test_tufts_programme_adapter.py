from __future__ import annotations

from datetime import date

import pytest

from gradwindow.programme_adapters.tufts import (
    CATALOG_URL,
    DEADLINES_URL,
    TuftsAdapter,
)

ART_URL = "https://asegrad.tufts.edu/program/art-education-masters"
VET_URL = "https://vet.tufts.edu/masters-programs/ms-animals-and-public-policy"

CATALOG_HTML = f"""
<html><body>
  <article class="node--type-program">
    <h4 class="program--title">Art Education - Master's</h4>
    <div class="program--degree">Master's</div>
    <div class="icon-program--schools">Graduate School of Arts and Sciences</div>
    <a class="program--cta" href="{ART_URL}?utm_source=tufts.edu"></a>
  </article>
  <article class="node--type-program">
    <h4 class="program--title">Animals and Public Policy - Master's</h4>
    <div class="program--degree">Master's</div>
    <div class="icon-program--schools">Cummings School of Veterinary Medicine</div>
    <a class="program--cta" href="{VET_URL}?utm_source=tufts.edu"></a>
  </article>
  <article class="node--type-program">
    <h4 class="program--title">History - Doctorate</h4>
    <div class="program--degree">Master's and Doctorate</div>
    <div class="icon-program--schools">Graduate School of Arts and Sciences</div>
    <a class="program--cta" href="https://asegrad.tufts.edu/program/history-doctorate"></a>
  </article>
</body></html>
"""

DEADLINES_HTML = f"""
<html><body><table><thead><tr>
  <th>Program</th><th>Fall</th><th>Spring</th><th>Summer</th>
</tr></thead><tbody><tr>
  <td><a href="{ART_URL}">Art Education</a></td>
  <td>January 15 (priority), April 15 (regular), rolling through August 1</td>
  <td>n/a</td><td>n/a</td>
</tr></tbody></table></body></html>
"""


def _adapter(**overrides) -> TuftsAdapter:
    return TuftsAdapter(
        minimum_expected_programmes=overrides.get("minimum_expected_programmes", 2),
        minimum_expected_deadline_programmes=overrides.get(
            "minimum_expected_deadline_programmes", 1
        ),
        reference_date=date(2026, 8, 29),
    )


def _fetcher(url: str) -> str:
    return {CATALOG_URL: CATALOG_HTML, DEADLINES_URL: DEADLINES_HTML}[url]


def test_tufts_separates_university_identities_from_ase_deadlines() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)
    programmes = {item.name: item for item in catalog.programmes}
    art = programmes["Art Education"]
    vet = programmes["Animals and Public Policy"]

    assert art.faculty == "Graduate School of Arts and Sciences"
    assert art.source_url == ART_URL
    assert [window.round for window in art.windows] == [
        "Priority deadline",
        "Regular deadline",
        "Rolling final deadline",
    ]
    assert [window.closes_at for window in art.windows] == [
        "2027-01-15",
        "2027-04-15",
        "2027-08-01",
    ]
    assert all(window.intake == "Fall 2027" for window in art.windows)
    assert all(window.opens_at is None for window in art.windows)
    assert art.parse_status == "incomplete"
    assert vet.windows == []
    assert vet.parse_status == "no-deadline"


def test_tufts_excludes_a_doctorate_card_with_a_combined_filter_label() -> None:
    catalog = _adapter().parse_catalog_from_fetcher(_fetcher)

    assert "History - Doctorate" not in {item.name for item in catalog.programmes}


def test_tufts_no_longer_depends_on_university_marketing_copy() -> None:
    requested: list[str] = []

    def fetcher(url: str) -> str:
        requested.append(url)
        return _fetcher(url)

    _adapter().parse_catalog_from_fetcher(fetcher)

    assert requested == [CATALOG_URL, DEADLINES_URL]


def test_tufts_rejects_a_truncated_deadline_table() -> None:
    with pytest.raises(ValueError, match="matched 1 master's programme"):
        _adapter(minimum_expected_deadline_programmes=2).parse_catalog_from_fetcher(
            _fetcher
        )
