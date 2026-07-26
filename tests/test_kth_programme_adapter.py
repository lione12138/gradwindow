import pytest

from gradwindow.programme_adapters.kth import KTHAdapter

HTML = """<h2>Electrical Engineering and Computer Science</h2><a href="/en/studies/master/computer-science">Computer Science</a><a href="/en/studies/master/machine-learning">Machine Learning</a><a href="/en/studies/master/programmes/subjects">Programmes by subject</a>"""


def test_kth_parses_only_programme_detail_links() -> None:
    catalog = KTHAdapter(minimum_expected_programmes=2).parse_catalog(HTML)
    assert {item.id for item in catalog.programmes} == {
        "kth-computer-science-msc",
        "kth-machine-learning-msc",
    }


def test_kth_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        KTHAdapter(minimum_expected_programmes=3).parse_catalog(HTML)
