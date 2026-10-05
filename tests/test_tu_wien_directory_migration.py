import pytest

from gradwindow.programme_adapters.tu_wien import CATALOG_URL, TUWienAdapter


def test_follows_both_language_lists_and_deduplicates_featured_programme():
    german = CATALOG_URL + "/deutschsprachige-masterstudien"
    english = CATALOG_URL + "/english-taught-masters-programmes"
    physics = '<a href="/en/studies/studies/master-programmes/physics/technical-physics">Technical Physics</a>'
    pages = {
        CATALOG_URL: f'<main><a href="{german}">German</a><a href="{english}">English</a>{physics}</main>',
        german: '<main><a href="/en/studies/studies/master-programmes/architecture-and-planning/architecture">Architecture</a></main>',
        english: f"""<main>{physics}
        <a href="https://informatics.tuwien.ac.at/master/double-degree-it-security/">Double Degree IT Security</a>
        <a href="/en/studies/studies/master-programmes/physics">Physics category</a>
        <a href="https://example.org/en/studies/studies/master-programmes/physics/fake">Fake</a></main>""",
    }
    adapter = TUWienAdapter()
    adapter.minimum_expected_programmes = 3
    programmes = adapter.parse_catalog_from_fetcher(pages.__getitem__).programmes
    assert [p.name for p in programmes] == [
        "Architecture",
        "Double Degree IT Security",
        "Technical Physics",
    ]
    assert all(not p.windows for p in programmes)


def test_missing_language_list_fails_instead_of_partial_catalogue():
    adapter = TUWienAdapter()
    adapter.minimum_expected_programmes = 1
    with pytest.raises(ValueError, match="language directories"):
        adapter.parse_catalog_from_fetcher(
            lambda _: (
                '<main><a href="/en/studies/studies/master-programmes/english-taught-masters-programmes">English</a></main>'
            )
        )
