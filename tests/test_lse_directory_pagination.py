import pytest

from gradwindow.programme_adapters.lse import LSEAdapter

URL = "https://www.lse.ac.uk/programmes/search-courses"


def page(start, end, total, names):
    links = "".join(
        f'<a href="/study-at-lse/graduate/{slug}">{name}</a>' for slug, name in names
    )
    return f"<main>Showing {start}-{end} results of {total}{links}</main>"


def test_lse_reads_all_pages_and_excludes_research():
    pages = {
        URL: page(
            1, 2, 3, [("msc-finance", "MSc Finance"), ("phd-law", "MPhil/PhD Law")]
        ),
        URL + "?pageIndex=2": page(3, 3, 3, [("msc-economics", "MSc Economics")]),
    }
    adapter = LSEAdapter()
    adapter.minimum_expected_programmes = 2
    catalog = adapter.parse_catalog_from_fetcher(pages.__getitem__)
    assert {p.name for p in catalog.programmes} == {"MSc Finance", "MSc Economics"}
    assert all(not p.windows for p in catalog.programmes)


@pytest.mark.parametrize(
    "second", [page(1, 2, 3, []), page(3, 3, 4, []), "Access denied"]
)
def test_lse_rejects_repeated_changed_or_missing_pagination(second):
    pages = {
        URL: page(1, 2, 3, [("msc-finance", "MSc Finance")]),
        URL + "?pageIndex=2": second,
    }
    adapter = LSEAdapter()
    adapter.minimum_expected_programmes = 1
    with pytest.raises(ValueError, match="pagination"):
        adapter.parse_catalog_from_fetcher(pages.__getitem__)
