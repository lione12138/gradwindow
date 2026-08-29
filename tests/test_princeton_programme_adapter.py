from __future__ import annotations

import pytest

from gradwindow.programme_adapters.princeton import (
    APPLICATION_URL,
    CATALOG_URL,
    DEADLINES_URL,
    PrincetonAdapter,
)

CATALOG_MARKDOWN = """
| Departments & Programs | Program Offerings |
| --- | --- |
| [Architecture](https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/architecture) | Ph.D. , M.Arch. |
| [Chemical and Biological Engineering](https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/chemical-and-biological-engineering) | Ph.D. , M.S.E. , M.Eng. |
| [Chemistry](https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/chemistry) | Ph.D. , M.S. |
| [Electrical and Computer Engineering](https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/electrical-and-computer-engineering) | Ph.D. , M.Eng. |
| [Anthropology](https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/anthropology) | Ph.D. |
"""

DEADLINES_HTML = """
<html><body>
  <p>The application for Fall 2027 will open on September 15, 2026.</p>
  <table>
    <tr><th>Deadline</th><th>Fields of study</th></tr>
    <tr><td>December 1</td><td><ul><li>Biological Engineering</li><li>Chemical and Biological Engineering</li><li>Chemistry</li></ul></td></tr>
    <tr><td>December 15</td><td><ul><li>Electrical and Computer Engineering - Ph.D.</li></ul></td></tr>
    <tr><td>December 21</td><td><ul><li>Architecture</li><li>Electrical and Computer Engineering - M.Eng.</li></ul></td></tr>
  </table>
</body></html>
"""


def _fetcher(url: str) -> str:
    if url == CATALOG_URL:
        return CATALOG_MARKDOWN
    if url == DEADLINES_URL:
        return DEADLINES_HTML
    raise AssertionError(f"unexpected request: {url}")


def test_princeton_adapter_uses_only_the_two_central_pages() -> None:
    requested: list[str] = []

    def fetcher(url: str) -> str:
        requested.append(url)
        return _fetcher(url)

    catalog = PrincetonAdapter(
        minimum_expected_programmes=5
    ).parse_catalog_from_fetcher(fetcher)

    assert requested == [CATALOG_URL, DEADLINES_URL]
    assert catalog.application_opens_at is None
    assert [programme.id for programme in catalog.programmes] == [
        "princeton-architecture-march",
        "princeton-chemical-and-biological-engineering-meng",
        "princeton-chemical-and-biological-engineering-mse",
        "princeton-chemistry-ms",
        "princeton-electrical-and-computer-engineering-meng",
    ]
    assert [programme.windows[0].closes_at for programme in catalog.programmes] == [
        "2026-12-21",
        "2026-12-01",
        "2026-12-01",
        "2026-12-01",
        "2026-12-21",
    ]
    assert all(
        programme.windows[0].opens_at == "2026-09-15"
        for programme in catalog.programmes
    )
    assert all(
        programme.windows[0].intake == "Fall 2027" for programme in catalog.programmes
    )
    assert all(programme.parse_status == "parsed" for programme in catalog.programmes)
    assert all(
        programme.retrieval_method == "official-html"
        for programme in catalog.programmes
    )


def test_princeton_adapter_preserves_urls_and_restricted_chemistry_policy() -> None:
    catalog = PrincetonAdapter(
        minimum_expected_programmes=5
    ).parse_catalog_from_fetcher(_fetcher)
    architecture = catalog.programmes[0]
    chemistry = next(
        item for item in catalog.programmes if item.department == "Chemistry"
    )

    assert architecture.name == "M.Arch. in Architecture"
    assert architecture.degree_type == "MARCH"
    assert architecture.faculty == "Princeton University Graduate School"
    assert architecture.source_url.endswith("/fields-study/architecture")
    assert architecture.application_url == APPLICATION_URL
    assert architecture.windows[0].source_url == DEADLINES_URL
    assert architecture.windows[0].opens_at_basis == "official"
    assert architecture.admission_route == "direct-master"
    assert chemistry.admission_route == "restricted-master"
    assert "Industrial Associates Program" in chemistry.deadline_text


def test_princeton_adapter_does_not_apply_the_ece_phd_deadline_to_meng() -> None:
    catalog = PrincetonAdapter(
        minimum_expected_programmes=5
    ).parse_catalog_from_fetcher(_fetcher)
    ece = next(
        item
        for item in catalog.programmes
        if item.department == "Electrical and Computer Engineering"
    )

    assert ece.windows[0].closes_at == "2026-12-21"


def test_princeton_adapter_uses_the_existing_computer_science_id() -> None:
    catalog_markdown = CATALOG_MARKDOWN.replace(
        "| [Anthropology]",
        "| [Computer Science](https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/computer-science) | Ph.D. , M.S.E. |\n| [Anthropology]",
    )
    deadlines_html = DEADLINES_HTML.replace(
        "<li>Electrical and Computer Engineering - Ph.D.</li>",
        "<li>Computer Science</li><li>Electrical and Computer Engineering - Ph.D.</li>",
    )

    def fetcher(url: str) -> str:
        if url == CATALOG_URL:
            return catalog_markdown
        if url == DEADLINES_URL:
            return deadlines_html
        raise AssertionError(url)

    catalog = PrincetonAdapter(
        minimum_expected_programmes=6
    ).parse_catalog_from_fetcher(fetcher)
    computer_science = next(
        item for item in catalog.programmes if item.department == "Computer Science"
    )

    assert computer_science.id == "princeton-computer-science-mse"
    assert computer_science.name == "MSE in Computer Science"


def test_princeton_adapter_rejects_a_truncated_masters_catalogue() -> None:
    with pytest.raises(ValueError, match="only contained 5 master's programmes"):
        PrincetonAdapter(minimum_expected_programmes=6).parse_catalog_from_fetcher(
            _fetcher
        )


def test_princeton_adapter_requires_an_exact_official_opening_date() -> None:
    def fetcher(url: str) -> str:
        if url == DEADLINES_URL:
            return DEADLINES_HTML.replace("September 15, 2026", "September 2026")
        return _fetcher(url)

    with pytest.raises(ValueError, match="no exact opening date"):
        PrincetonAdapter(minimum_expected_programmes=5).parse_catalog_from_fetcher(
            fetcher
        )


def test_princeton_adapter_rejects_a_missing_central_deadline() -> None:
    def fetcher(url: str) -> str:
        if url == DEADLINES_URL:
            return DEADLINES_HTML.replace("<li>Architecture</li>", "")
        return _fetcher(url)

    with pytest.raises(ValueError, match="Architecture M.Arch"):
        PrincetonAdapter(minimum_expected_programmes=5).parse_catalog_from_fetcher(
            fetcher
        )
