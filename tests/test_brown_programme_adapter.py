import pytest

from gradwindow.programme_adapters.brown import BrownAdapter

HTML = """<div class="views-row"><div class="term-item hidden">Master Program</div><div class="views-field-field-program-degree-type">Sc.M.</div><h2><a href="/graduate-program/computer-science-scm">Computer Science</a></h2></div><div class="views-row"><div class="term-item">Doctoral Program</div><div class="views-field-field-program-degree-type">Ph.D.</div><h2><a href="/phd">History</a></h2></div>"""


def test_brown_keeps_only_master_cards() -> None:
    catalog = BrownAdapter(minimum_expected_programmes=1).parse_catalog(HTML)
    assert [item.id for item in catalog.programmes] == ["brown-computer-science-scm"]
    assert catalog.programmes[0].degree_type == "Sc.M."


def test_brown_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 2"):
        BrownAdapter(minimum_expected_programmes=2).parse_catalog(HTML)
