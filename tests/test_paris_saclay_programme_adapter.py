import pytest

from gradwindow.programme_adapters.paris_saclay import ParisSaclayAdapter

HTML = """<article class="licence"><a href="/en/education/masters-degree/computer-science"><h3>Computer Science</h3><p>Master's degree</p></a></article><article class="licence"><a href="/en/education/masters-degree/economics"><h3>Economics</h3></a></article>"""


def test_paris_saclay_discovers_master_fields_without_inferred_dates() -> None:
    catalog = ParisSaclayAdapter(minimum_expected_programmes=2).parse_catalog(HTML)
    assert {item.id for item in catalog.programmes} == {
        "paris-saclay-computer-science-master",
        "paris-saclay-economics-master",
    }
    assert all(item.windows == [] for item in catalog.programmes)


def test_paris_saclay_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        ParisSaclayAdapter(minimum_expected_programmes=3).parse_catalog(HTML)
