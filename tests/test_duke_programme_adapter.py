import pytest

from gradwindow.programme_adapters.duke import DukeAdapter

HTML = '<a href="/academics/programs-degrees/computer-science-ms/">Computer Science</a><a href="/academics/programs-degrees/economics-masters/">Economics</a>'


def test_duke_discovers_masters_without_inferred_opening_dates() -> None:
    catalog = DukeAdapter(minimum_expected_programmes=2).parse_catalog(HTML)
    assert {item.id for item in catalog.programmes} == {
        "duke-computer-science-ms",
        "duke-economics-master",
    }
    assert all(
        item.windows == [] and item.parse_status == "no-deadline"
        for item in catalog.programmes
    )


def test_duke_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        DukeAdapter(minimum_expected_programmes=3).parse_catalog(HTML)
